import logging

import pytest
from zellular.zellular import Zellular
from zellular.networks.eigenlayer import EigenlayerNetwork

logger = logging.getLogger(__name__)


@pytest.fixture
def verifier() -> Zellular:
    network = EigenlayerNetwork(
        subgraph_url="https://api.studio.thegraph.com/query/95922/avs-subgraph/v0.0.3",
        threshold_percent=40,
    )
    return Zellular(app="simple_app", network=network)


def test_blocking_send(verifier: Zellular, generate_test_tx: str) -> None:
    index = verifier.send(generate_test_tx, blocking=True)
    logger.info(f"The sent batch sequenced at {index}")
    assert index is not None and index > 0
