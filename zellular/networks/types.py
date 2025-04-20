from dataclasses import dataclass


@dataclass
class Operator:
    id: str
    address: str
    socket: str
    stake: float
    public_key_g2: object
