import logging
import json
import random
import asyncio
import requests
from typing import Generator
import xxhash
import aiohttp
from packaging.version import parse as parse_version

from zellular.networks.base import Network
from zellular.networks.types import Operator

hash = xxhash.xxh128_hexdigest
logger = logging.getLogger(__name__)

class Zellular:
    """
    Zellular client for interacting with a distributed app's sequencer network.

    This class provides methods to:
    - Fetch finalized batches for a given app
    - Submit new batches and optionally wait for finalization
    - Verify the consensus state of finalized data
    - Dynamically discover a healthy gateway node from active operators

    It operates over a pluggable `Network` backend (e.g., Eigenlayer or Static), allowing
    the same logic to work with different network topologies and consensus mechanisms.

    If no gateway is provided at initialization, a random active operator running the latest
    software version and up-to-date consensus state will be selected.

    Args:
        app (str): The app name this client is associated with.
        network (Network): The network instance to use (e.g., EigenlayerNetwork).
        gateway (str | None): Optional override for the gateway node (http(s)://host:port).
    """
    def __init__(self, app: str, network: Network, gateway: str | None = None):
        self.app = app
        self.network = network
        self.gateway = gateway or self._get_random_active_operator(app).socket

    def batches(self, after: int = 0) -> Generator[tuple[str, int], None, None]:
        assert after >= 0, "after should be equal or bigger than 0"
        chaining_hash: str | None = "" if after == 0 else None

        while True:
            chaining_hash, batch_list = self._get_finalized_batches(
                after, chaining_hash
            )
            for batch in batch_list:
                after += 1
                yield batch, after

    def get_last_finalized(self, socket: str | None = None) -> dict:
        url = f"{socket or self.gateway}/node/{self.app}/batches/finalized/last"
        response = requests.get(url, timeout=3)
        assert response.status_code == 200, f"request failed with status code: {response.status_code}, {response.text}"
        result = response.json()
        assert result["status"] == "success", f"request failed with message {message}"
        data = result["data"]
        if data == {}:
            # There is no finalized batch yet
            return data

        verified = self._verify_finalized(
            data["index"],
            data["hash"],
            data["chaining_hash"],
            data["finalized_nonsigners"],
            data["finalized_tag"],
            data["finalization_signature"],
        )
        assert verified, f"the finalized batch verification failed! {data}"
        return data

    def send(self, batch: dict, blocking: bool = False) -> int | None:
        if blocking:
            index = self.get_last_finalized().get("index", 0)

        url = f"{self.gateway}/node/{self.app}/batches"
        response = requests.put(url, json=batch)
        assert response.status_code == 200, response.text
        if not blocking:
            return None

        for received_batch, idx in self.batches(after=index):
            received_batch_json = json.loads(received_batch)
            if batch == received_batch_json:
                return idx

    def _verify_finalized(
        self,
        index: int,
        batch_hash: str,
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
                "hash": batch_hash,
                "chaining_hash": chaining_hash,
            },
            sort_keys=True,
        )
        result = self.network.verify_signature(message, signature, nonsigners, tag)
        logger.info(f"app: {self.app}, index: {index}, verification result: {result}")
        return result

    def _get_finalized_batches(
        self, after: int, chaining_hash: str | None
    ) -> tuple[str, list[str]]:
        res = []
        index = after if chaining_hash is not None else after - 1

        while True:
            response = requests.get(
                f"{self.gateway}/node/{self.app}/batches/finalized?after={index}"
            )
            assert response.status_code == 200, response.text

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
                    assert self._verify_finalized(
                        index,
                        hash(batch),
                        chaining_hash,
                        finalized["nonsigners"],
                        finalized["tag"],
                        finalized["signature"],
                    ), "invalid signature"
                    return chaining_hash, res

    async def _fetch_node_state(self, operator: Operator, app: str) -> tuple[Operator, int, int, str] | None:
        url = f"{operator.socket}/node/state"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    node_data = data.get("data", {})
                    app_data = node_data.get("apps", {}).get(app)
                    version = node_data.get("version")
                    if not app_data or not version:
                        return None
                    return operator, app_data["last_finalized_index"], app_data["last_locked_index"], version
        except Exception as e:
            return None


    async def get_active_operators(self, app: str) -> list[Operator]:
        # Step 1: Get the current list of known operators from the network
        operators = self.network.get_operators()

        # Step 2: Asynchronously query each operator's `/node/state` endpoint for the given app
        tasks = [self._fetch_node_state(op, app) for op in operators.values()]
        results = await asyncio.gather(*tasks)

        # Step 3: Filter out operators that did not respond or returned incomplete data
        # This also filters out the leader as unlike nodes, the leader does not respond to the state query
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
        return [op for op, _, locked, _ in version_matched if locked >= highest_finalized]

    def _get_random_active_operator(self, app: str) -> Operator:
        operators = asyncio.run(self.get_active_operators(app))
        if not operators:
            raise RuntimeError("No active operators found")
        return random.choice(operators)