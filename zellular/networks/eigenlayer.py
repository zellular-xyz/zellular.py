import requests
from typing import Any

from zellular.networks.types import Operator
from zellular.networks.base import Network


class EigenlayerNetwork(Network):
    """Implementation for EigenLayer-based operator discovery.

    Fetches operator data from an EigenLayer subgraph for dynamically
    discovering operator stake, endpoints, and cryptographic keys.
    """

    DEFAULT_NODES = {
        "0x747b80a1c0b0e6031b389e3b7eaf9b5f759f34ed",
        "0x3eaa1c283dbf13357257e652649784a4cc08078c",
        "0x906585f83fa7d29b96642aa8f7b4267ab42b7b6c",
        "0x93d89ade53b8fcca53736be1a0d11d342d71118b",
    }

    def __init__(self, subgraph_url: str, threshold_percent: float):
        super().__init__(threshold_percent)
        self.subgraph_url = subgraph_url

    def get_tag(self) -> str:
        """Get block number as network state identifier with safety margin."""
        query = "{ _meta { block { number } } }"
        response = requests.post(
            self.subgraph_url,
            headers={"content-type": "application/json"},
            json={"query": query},
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch block number (status {response.status_code}): "
                f"{response.text}"
            )

        try:
            block_number = int(response.json()["data"]["_meta"]["block"]["number"])
            # add a delay to ensure no reorg happens
            return str(block_number - 5)
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(
                f"Unexpected response format while parsing block number: "
                f"{response.text}, error: {e}"
            )

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
            raise RuntimeError(
                f"Failed to fetch operators (status {response.status_code}): "
                f"{response.text}"
            )

        try:
            operators = response.json().get("data", {}).get("operators", [])
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(
                f"Unexpected response format while parsing operators: "
                f"{response.text}, error: {e}"
            )

        return {
            op["id"]: Operator(
                id=op["id"],
                address=op["id"],
                socket=op["socket"],
                stake=EigenlayerNetwork._get_stake(op),
                public_key_g2=EigenlayerNetwork._get_g2_key(op),
                roles=["posting", "sequencing"],
            )
            for op in operators
        }

    @classmethod
    def _get_stake(cls, operator: dict[str, Any]) -> float:
        stake = int(operator.get("stake", 0)) / (10**18)
        return stake if operator.get("id") in cls.DEFAULT_NODES else min(stake, 1)
