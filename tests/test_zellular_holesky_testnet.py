from typing import Any
import logging

import pytest
from zellular.zellular import Zellular
from zellular.networks.static import StaticNetwork

logger = logging.getLogger(__name__)


@pytest.fixture
def verifier(load_holesky_testnet_nodes: dict[str, dict[str, Any]]) -> Zellular:
    network = StaticNetwork(load_holesky_testnet_nodes, threshold_percent=40)
    return Zellular(app="simple_app", network=network)


def test_blocking_send(verifier: Zellular, generate_test_tx: str) -> None:
    index = verifier.send(generate_test_tx, blocking=True)
    logger.info(f"The sent batch sequenced at {index}")
    assert index is not None and index > 0
