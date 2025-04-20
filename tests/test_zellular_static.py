import json
import os
import pytest
from zellular.zellular import Zellular
from zellular.networks.static import StaticNetwork


@pytest.fixture
def static_verifier():
    nodes_file = os.path.join(os.path.dirname(__file__), "nodes.json")
    with open(nodes_file) as f:
        nodes_data = json.load(f)

    network = StaticNetwork(nodes_data, threshold_percent=40)
    return Zellular(app="simple_app", network=network)


def test_static_zellular_batches_and_last_finalized(static_verifier: Zellular):
    # Test batches stream
    index = static_verifier.send("This is a test batch", blocking=True)
    print(f"The sent batch sequenced at {index}")

    stream = static_verifier.batches()
    batch, index = next(stream)

    assert isinstance(batch, str)
    assert isinstance(index, int)
    assert index > 0
    print(f"First batch at index {index}: {batch}")

    # Test get_last_finalized
    finalized = static_verifier.get_last_finalized()
    assert finalized is not None
    assert "index" in finalized
    assert "hash" in finalized
    assert "chaining_hash" in finalized
    print(f"Last finalized index: {finalized['index']}")
