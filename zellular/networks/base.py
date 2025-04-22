from abc import ABC, abstractmethod
from eigensdk.crypto.bls import attestation
from .types import Operator
from .utils import aggregate_g2_keys
import xxhash

hash = xxhash.xxh128_hexdigest


class Network(ABC):
    def __init__(self, threshold_percent: float = 67):
        self.threshold_percent = threshold_percent
        self._cache: dict[str, dict[str, Operator]] = {}
        self._agg_cache: dict[str, attestation.G2Point] = {}

    @abstractmethod
    def _load_operators(self, tag: str | None) -> dict[str, Operator]:
        pass

    @abstractmethod
    def get_tag(self) -> str:
        pass

    def get_operators(self, tag: str | None = None) -> dict[str, Operator]:
        if tag is not None and tag in self._cache:
            return self._cache[tag]

        operators = self._load_operators(tag)

        if tag is not None:
            self._cache[tag] = operators

        return operators

    def _get_aggregated_public_key(self, tag: str | None = None) -> attestation.G2Point:
        if tag is not None and tag in self._agg_cache:
            return self._agg_cache[tag]

        operators = self.get_operators(tag)
        aggregated_public_key = aggregate_g2_keys(list(operators.values()))

        if tag is not None:
            self._agg_cache[tag] = aggregated_public_key

        return aggregated_public_key

    def verify_signature(
        self,
        message: str,
        signature_hex: str,
        nonsigners: list[str],
        tag: str | None = None,
    ) -> bool:
        operators = self.get_operators(tag)
        total_stake = sum(operator.stake for operator in operators.values())
        nonsigner_operators = [operators[_id] for _id in nonsigners if _id in operators]
        nonsigners_stake = sum(op.stake for op in nonsigner_operators)

        if 100 * nonsigners_stake / total_stake > 100 - self.threshold_percent:
            return False

        public_key = self._get_aggregated_public_key(tag)
        for op in nonsigner_operators:
            public_key -= op.public_key_g2

        signature = attestation.new_zero_signature()
        signature.setStr(signature_hex.encode("utf-8"))

        hashed_message = hash(message)
        return signature.verify(public_key, str(hashed_message).encode("utf-8"))
