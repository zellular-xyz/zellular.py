from typing import Any

from zellular.networks.base import Network
from zellular.networks.types import Operator


class StaticNetwork(Network):
    """Implementation for fixed, predefined operator sets.

    Loads operator data from a static source for testing, development,
    or proof-of-authority deployments with stable operator membership.

    The operator data must be provided as a dictionary mapping operator IDs to
    metadata dictionaries. Each operator entry should include the following fields:

        {
            "id": "<operator_id>",
            "address": "<operator_address>",
            "socket": "http(s)://<host:port>",
            "stake": "<operator_weight>",
            "pubkeyG2_X": [X0, X1],
            "pubkeyG2_Y": [Y0, Y1],
        }
    """

    def __init__(
        self, operator_data: dict[str, dict[str, Any]], threshold_percent: float = 67
    ):
        super().__init__(threshold_percent)
        self._operator_data = operator_data

    def get_tag(self) -> str:
        """
        Returns a constant tag identifier for the static network.
        """
        return "latest"

    def _load_operators(self, tag: str | None) -> dict[str, Operator]:
        return {
            op["id"]: Operator(
                id=op["id"],
                address=op["id"],
                socket=op["socket"],
                stake=float(op["stake"]),
                public_key_g2=StaticNetwork._get_g2_key(op),
                roles=op["roles"] if "roles" in op else ["posting", "sequencing"],
            )
            for op in self._operator_data.values()
        }
