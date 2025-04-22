from .base import Network
from .types import Operator
from .utils import parse_g2_key


class StaticNetwork(Network):
    """
    A `Network` implementation that loads operator data from a static source.

    This is intended for proof-of-authority (PoA) deployments or testing environments,
    where the set of operators is predefined (e.g. loaded from a local nodes.json file)
    and does not rely on dynamic discovery or staking mechanisms.

    Use this class when operator membership is fixed and controlled, rather than
    delegated or determined by stake (as in EigenLayer-based networks).

    The operator data must be provided as a dictionary mapping operator IDs to
    metadata dictionaries. Each operator entry should include the following fields:

        {
            "id": "<operator_id>",                      # Operator address (same as the key)
            "address": "<operator_address>",            # Redundant, matches "id"
            "socket": "<host:port>",                    # Publicly reachable RPC endpoint
            "stake": <numeric stake>,                   # Float or int (used in weighted quorum)
            "public_key_g2": "<BLS G2 pubkey as string>"# Formatted as: "1 x1 x2 y1 y2"
        }
    """

    def __init__(self, operator_data: dict[str, dict], threshold_percent: float = 67):
        super().__init__(threshold_percent)
        self._operator_data = operator_data

    def get_tag(self) -> str:
        return "latest"

    def _load_operators(self, tag: str | None) -> dict[str, Operator]:
        return {
            op["id"]: Operator(
                id=op["id"],
                address=op["id"],
                socket=op["socket"],
                stake=float(op["stake"]),
                public_key_g2=parse_g2_key(op),
            )
            for op in self._operator_data.values()
        }
