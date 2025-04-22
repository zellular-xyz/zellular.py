import requests
from .utils import parse_g2_key
from .types import Operator
from .base import Network

class EigenlayerNetwork(Network):
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

    def get_tag(self) -> str:
        query = "{ _meta { block { number } } }"
        response = requests.post(
            self.subgraph_url,
            headers={"content-type": "application/json"},
            json={"query": query},
        )

        if response.status_code == 200:
            block_number = int(response.json()["data"]["_meta"]["block"]["number"])
            return str(block_number - 5)
        else:
            raise Exception(f"Failed to fetch block number: {response.text}")

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
            raise Exception(f"Failed to fetch operators: {response.text}")

        operators = response.json().get("data", {}).get("operators", [])

        return {
            op["id"]: Operator(
                id=op["id"],
                address=op["id"],
                socket=op["socket"],
                stake=self._get_stake(op),
                public_key_g2=parse_g2_key(op),
            )
            for op in operators
        }
