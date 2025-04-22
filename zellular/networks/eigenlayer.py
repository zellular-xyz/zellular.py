import requests
from eigensdk.crypto.bls import attestation

from .types import Operator
from .base import Network

class EigenlayerNetwork(Network):
    """
    A `Network` implementation for loading operator data from an EigenLayer subgraph.

    This class fetches operator stake, socket info, and BLS keys from a configured subgraph
    endpoint. Stake values are adjusted based on testnet-specific constraints: whitelisted
    nodes retain full stake, while others are capped to simulate participation thresholds.

    Signature verification and quorum enforcement are handled by the base `Network` class,
    using aggregated BLS public keys and a configurable stake threshold.
    """

    DEFAULT_NODES = {
        "0x747b80a1c0b0e6031b389e3b7eaf9b5f759f34ed",
        "0x3eaa1c283dbf13357257e652649784a4cc08078c",
        "0x906585f83fa7d29b96642aa8f7b4267ab42b7b6c",
        "0x93d89ade53b8fcca53736be1a0d11d342d71118b",
    }

    def __init__(self, subgraph_url, threshold_percent):
        self.subgraph_url = subgraph_url
        super().__init__(threshold_percent)

    def _get_stake(self, operator: dict) -> float:
        stake = int(operator.get("stake", 0)) / (10**18)
        return stake if operator.get("id") in self.DEFAULT_NODES else min(stake, 1)

    def _get_g2_key(self, operator: dict) -> attestation.G2Point:
        return attestation.G2Point(operator['pubkeyG2_X'][0], operator['pubkeyG2_X'][1], operator['pubkeyG2_Y'][0], operator['pubkeyG2_Y'][1])

    def get_tag(self) -> str:
        query = "{ _meta { block { number } } }"
        response = requests.post(
            self.subgraph_url,
            headers={"content-type": "application/json"},
            json={"query": query},
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch block number (status {response.status_code}): {response.text}")

        try:
            block_number = int(response.json()["data"]["_meta"]["block"]["number"])
            # add a delay to ensure no reorg happens
            return str(block_number - 5)
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(f"Unexpected response format ({response.text}) while parsing block number: {e}")

    def _load_operators(self, tag: str | None) -> dict[str, Operator]:
        block_filter = f"(block: {{ number: {tag} }})" if tag else ""
        query = f"""
        {{
            operators{block_filter} {{
                id
                socket
                stake
                pubkeyG2_X
                pubkeyG2_Y
            }}
        }}
        """
        response = requests.post(
            self.subgraph_url,
            headers={"content-type": "application/json"},
            json={"query": query},
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch operators (status {response.status_code}): {response.text}")

        try:
            operators = response.json().get("data", {}).get("operators", [])
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(f"Unexpected response format ({response.text}) while parsing operators: {e}")

        return {
            op["id"]: Operator(
                id=op["id"],
                address=op["id"],
                socket=op["socket"],
                stake=self._get_stake(op),
                public_key_g2=self._get_g2_key(op),
            )
            for op in operators
        }
