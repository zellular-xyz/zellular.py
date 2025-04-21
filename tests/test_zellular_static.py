import json
import os
from uuid import uuid4
import pytest
from zellular.zellular import Zellular
from zellular.networks.static import StaticNetwork

@pytest.fixture
def verifier():
    nodes_file = os.path.join(os.path.dirname(__file__), "nodes.json")
    with open(nodes_file) as f:
        nodes_data = json.load(f)

    network = StaticNetwork(nodes_data, threshold_percent=30)
    return Zellular(app="simple_app", network=network)

def test_blocking_send(verifier):
    tx = { "tx_id": str(uuid4()), "operation": "foo" }
    index = verifier.send(tx, blocking=True)
    print(f"The sent batch sequenced at {index}")
    assert index > 0

