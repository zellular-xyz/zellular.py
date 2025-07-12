import httpx
import logging
import json
import random
import asyncio
from contextlib import aclosing
from typing import Any, AsyncGenerator, Generator
import xxhash
from packaging.version import parse as parse_version

from zellular.networks.base import Network
from zellular.networks.types import Operator

hash = xxhash.xxh128_hexdigest
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


class ZellularAsync:
    """
    Zellular async client for interacting with a distributed app's sequencer network.

    This class provides methods to:
    - Fetch finalized batches for a given app
    - Submit new batches and optionally wait for finalization
    - Dynamically discover a healthy gateway node from active operators

    It operates over a pluggable network backend, enabling the same logic to work
    with different network topologies and consensus mechanisms.

    If no gateway is provided at initialization, a random active operator running the
    latest software version and up-to-date consensus state will be selected.
    """

    def __init__(
        self,
        app: str,
        network: Network,
        gateway: str | None = None,
        timeout: float = 5.0,
    ):
        self.client = httpx.AsyncClient()
        self.app = app
        self.network = network
        self.timeout = timeout
        self.gateway = gateway

    async def get_gateway(self):
        if not self.gateway:
            self.gateway = (await self._get_random_active_operator(self.app)).socket

        return self.gateway

    async def batches(self, after: int = 0) -> AsyncGenerator[tuple[str, int], None]:
        if after < 0:
            raise ValueError("Parameter 'after' should be equal to or greater than 0")
        chaining_hash: str | None = "" if after == 0 else None

        while True:
            chaining_hash, batch_list = await self._get_finalized_batches(
                after, chaining_hash
            )
            for batch in batch_list:
                after += 1
                yield batch, after

    async def get_last_finalized(self) -> dict[str, Any] | None:
        url = f"{await self.get_gateway()}/node/{self.app}/batches/finalized/last"
        response = await self.client.get(url, timeout=self.timeout)
        response.raise_for_status()

        result = response.json()
        if result["status"] != "success":
            raise ValueError(
                f"Request failed with message: {result.get('message', 'Unknown error')}"
            )

        data = result["data"]
        if data is None:
            # There is no finalized batch yet
            return data

        verified = self._verify_finalized(
            data["index"],
            data["chaining_hash"],
            data["finalized_nonsigners"] or [],
            data["finalized_tag"],
            data["finalization_signature"],
        )
        if not verified:
            raise ValueError(f"Finalized batch verification failed: {data}")
        return data

    async def send(self, batch: str, blocking: bool = False) -> int | None:
        if blocking:
            last_finalized = await self.get_last_finalized()
            index = last_finalized["index"] if last_finalized else 0

        url = f"{await self.get_gateway()}/node/{self.app}/batches"
        response = await self.client.put(
            url,
            content=batch,
            headers={"Content-Type": "text/plain"},
            timeout=self.timeout,
        )
        response.raise_for_status()

        if not blocking:
            return None

        async with aclosing(self.batches(after=index)) as gen:
            async for received_batch, idx in gen:
                if batch == received_batch:
                    return idx

        # This can never happen as batches method wait for new batches forever
        return None

    async def get_active_operators(self, app: str) -> list[Operator]:
        # Step 1: Get the current list of known posting operators from the network
        operators = self.network.get_operators(role="posting")
        # Step 2: Asynchronously query each operator's `/node/state` endpoint for the given app
        tasks = [self._fetch_node_state(op, app) for op in operators.values()]
        results = await asyncio.gather(*tasks)

        # Step 3: Filter out operators that did not respond or returned incomplete data
        filtered = [r for r in results if r]
        if not filtered:
            return []

        # Step 4: Determine the highest semantic version reported among the responsive operators
        highest_version = max(filtered, key=lambda r: parse_version(r[3]))[3]

        # Step 5: Keep only operators running the highest version
        version_matched = [r for r in filtered if r[3] == highest_version]
        if not version_matched:
            return []

        # Step 6: Determine the highest finalized index reported among version-matched operators
        highest_finalized = max(r[1] for r in version_matched)

        # Step 7: Return the subset of operators that have locked at or above the highest finalized index
        # These are considered actively participating in consensus
        return [
            op for op, _, locked, _ in version_matched if locked >= highest_finalized
        ]

    async def _get_random_active_operator(self, app: str) -> Operator:
        operators = await self.get_active_operators(app)
        if not operators:
            raise RuntimeError("No active operators found")
        return random.choice(operators)

    def _verify_finalized(
        self,
        index: int,
        chaining_hash: str,
        nonsigners: list[str],
        tag: str,
        signature: str,
    ) -> bool:
        message = json.dumps(
            {
                "app_name": self.app,
                "state": "locked",
                "index": index,
                "chaining_hash": chaining_hash,
            },
            sort_keys=True,
        )
        result = self.network.verify_signature(message, signature, nonsigners, tag)
        logger.info(f"app: {self.app}, index: {index}, verification result: {result}")
        return result

    async def _get_finalized_batches(
        self, after: int, chaining_hash: str | None
    ) -> tuple[str, list[str]]:
        res = []
        index = after if chaining_hash is not None else after - 1

        while True:
            response = await self.client.get(
                f"{await self.get_gateway()}/node/{self.app}/batches/finalized?after={index}",
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()["data"]
            if not data:
                continue

            batches = data["batches"]
            finalized = data["finalized"]

            if chaining_hash is None:
                chaining_hash = data["first_chaining_hash"]
                batches = batches[1:]
                index += 1

            for batch in batches:
                index += 1
                chaining_hash = hash(chaining_hash + hash(batch))
                res.append(batch)
                logger.info(f"finalized batch: {finalized}")
                if finalized and index == finalized["index"]:
                    if not self._verify_finalized(
                        index,
                        chaining_hash,
                        finalized["nonsigners"] or [],
                        finalized["tag"],
                        finalized["signature"],
                    ):
                        raise ValueError("Invalid signature for finalized batch")
                    return chaining_hash, res

    async def _fetch_node_state(
        self, operator: Operator, app: str
    ) -> tuple[Operator, int, int, str] | None:
        url = f"{operator.socket}/node/state"
        try:
            resp = await self.client.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
            node_data = data.get("data", {})

            # Skip sequencer nodes as they can't be directly connected to by clients
            if node_data.get("sequencer") is True:
                logger.info(f"Skipping sequencer node: {operator.id}")
                return None

            app_data = node_data.get("apps", {}).get(app)
            version = node_data.get("version")
            if not app_data or not version:
                return None
            return (
                operator,
                app_data["last_finalized_index"],
                app_data["last_locked_index"],
                version,
            )
        except Exception as e:
            logger.warning(
                f"Failed to load state of {operator.id} from {operator.socket}: {e}"
            )
            return None


class Zellular:
    """
    Zellular client for interacting with a distributed app's sequencer network.

    This class provides methods to:
    - Fetch finalized batches for a given app
    - Submit new batches and optionally wait for finalization
    - Dynamically discover a healthy gateway node from active operators

    It operates over a pluggable network backend, enabling the same logic to work
    with different network topologies and consensus mechanisms.

    If no gateway is provided at initialization, a random active operator running the
    latest software version and up-to-date consensus state will be selected.
    """

    def __init__(
        self,
        app: str,
        network: Network,
        gateway: str | None = None,
        timeout: float = 5.0,
    ):
        self._zellular = ZellularAsync(app, network, gateway, timeout)
        self._loop = asyncio.new_event_loop()

    def batches(self, after: int = 0) -> Generator[tuple[str, int], None, None]:
        # an async generator is pretty tricky to wrap in a sync
        # function, so we'll just duplicate this bit of code here.

        if after < 0:
            raise ValueError("Parameter 'after' should be equal to or greater than 0")
        chaining_hash: str | None = "" if after == 0 else None

        while True:
            chaining_hash, batch_list = self._loop.run_until_complete(
                self._zellular._get_finalized_batches(after, chaining_hash))
            for batch in batch_list:
                after += 1
                yield batch, after

    def get_last_finalized(self) -> dict[str, Any] | None:
        return self._loop.run_until_complete(self._zellular.get_last_finalized())

    def send(self, batch: str, blocking: bool = False) -> int | None:
        return self._loop.run_until_complete(self._zellular.send(batch, blocking))

    # this is supposed to be async in both versions
    async def get_active_operators(self, app: str) -> list[Operator]:
        return await self._zellular.get_active_operators(app)
