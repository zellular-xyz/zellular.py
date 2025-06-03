import logging
from abc import ABC, abstractmethod
from typing import Any

from eigensdk.crypto.bls import attestation
from zellular.networks.types import Operator, Role

import xxhash

hash = xxhash.xxh128_hexdigest
logger = logging.getLogger(__name__)


class Network(ABC):
    def __init__(self, threshold_percent: float = 67):
        self._threshold_percent = threshold_percent
        self._cache: dict[str, dict[str, Operator]] = {}
        self._agg_cache: dict[str, attestation.G2Point] = {}

    @abstractmethod
    def _load_operators(self, tag: str | None) -> dict[str, Operator]:
        pass

    @abstractmethod
    def get_tag(self) -> str:
        pass

    def get_operators(
        self, tag: str | None = None, role: Role | None = None
    ) -> dict[str, Operator]:
        if tag is not None and tag in self._cache:
            return self._cache[tag]

        operators = self._load_operators(tag)

        if tag is not None:
            self._cache[tag] = operators

        return {
            _id: operators[_id]
            for _id in operators
            if not role or role in operators[_id].roles
        }

    def verify_signature(
        self,
        message: str,
        signature_hex: str,
        nonsigners: list[str],
        tag: str | None = None,
    ) -> bool:
        """
        Verifies BLS signature and ensures sufficient stake for quorum.

        Args:
            message: The message that was signed, used for signature verification
            signature_hex: Hexadecimal representation of the BLS signature
            nonsigners: List of operator IDs that did not participate in signing.
                        Subtracted from the aggregated public key to create a
                        verification key representing only the signers.
            tag: Network state identifier for consistent verification across nodes.

        Returns:
            True if signature is valid and quorum requirements are met, False otherwise
        """
        operators = self.get_operators(tag)
        total_stake = sum(operator.stake for operator in operators.values())
        nonsigner_operators = [operators[id_] for id_ in nonsigners if id_ in operators]
        nonsigners_stake = sum(op.stake for op in nonsigner_operators)

        if 100 * nonsigners_stake / total_stake > 100 - self._threshold_percent:
            logger.warning(
                f"Signature rejected: nonsigners' stake ({nonsigners_stake}) exceeds allowed threshold. "
                f"Total stake: {total_stake}, threshold: {self._threshold_percent}%, "
                f"Nonsigners: {nonsigners}"
            )
            return False

        public_key = self._get_aggregated_public_key(tag)
        for op in nonsigner_operators:
            public_key -= op.public_key_g2

        signature = attestation.new_zero_signature()
        signature.setStr(signature_hex.encode("utf-8"))

        hashed_message = hash(message)
        valid = bool(signature.verify(public_key, str(hashed_message).encode("utf-8")))

        if not valid:
            logger.warning(
                f"Signature verification failed despite quorum being met. "
                f"Message: {message}, Tag: {tag}, Signature: {signature_hex}"
            )

        return valid

    def _get_aggregated_public_key(self, tag: str | None = None) -> attestation.G2Point:
        if tag is not None and tag in self._agg_cache:
            return self._agg_cache[tag]

        operators = self.get_operators(tag)

        aggregated_public_key = attestation.new_zero_g2_point()
        for op in operators.values():
            if op.stake > 0:
                aggregated_public_key += op.public_key_g2

        if tag is not None:
            self._agg_cache[tag] = aggregated_public_key

        return aggregated_public_key

    @staticmethod
    def _get_g2_key(operator: dict[str, Any]) -> attestation.G2Point:
        return attestation.G2Point(
            operator["pubkeyG2_X"][0],
            operator["pubkeyG2_X"][1],
            operator["pubkeyG2_Y"][0],
            operator["pubkeyG2_Y"][1],
        )
