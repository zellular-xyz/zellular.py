from typing import Any

import pytest
from zellular.zellular import Zellular
from zellular.networks.eigenlayer import EigenlayerNetwork


@pytest.fixture
def verifier() -> Zellular:
    """Create a Zellular client with EigenlayerNetwork for testing."""
    network = EigenlayerNetwork(
        subgraph_url="https://api.studio.thegraph.com/query/95922/avs-subgraph/v0.0.3",
        threshold_percent=40,
    )
    return Zellular(app="simple_app", network=network)


def test_blocking_send(verifier: Zellular, generate_test_tx: dict[str, Any]) -> None:
    """Test sending a transaction with blocking mode."""
    index = verifier.send(generate_test_tx, blocking=True)
    print(f"The sent batch sequenced at {index}")
    assert index is not None and index > 0
