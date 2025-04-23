from dataclasses import dataclass
from eigensdk.crypto.bls.attestation import G2Point


@dataclass
class Operator:
    id: str
    address: str
    socket: str
    stake: float
    public_key_g2: G2Point
