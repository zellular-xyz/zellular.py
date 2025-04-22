import json
from uuid import uuid4
import pytest
from zellular.zellular import Zellular
from zellular.networks.eigenlayer import EigenlayerNetwork


@pytest.fixture
def verifier():
    network = EigenlayerNetwork(
        subgraph_url="https://api.studio.thegraph.com/query/95922/avs-subgraph/v0.0.3",
        threshold_percent=40,
    )
    return Zellular(app="simple_app", network=network)


def test_blocking_send(verifier):
    tx = {"tx_id": str(uuid4()), "operation": "foo"}
    index = verifier.send(tx, blocking=True)
    print(f"The sent batch sequenced at {index}")
    assert index > 0
