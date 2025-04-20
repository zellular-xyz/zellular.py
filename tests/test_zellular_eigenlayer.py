import json
import pytest
from zellular.zellular import Zellular
from zellular.networks.eigenlayer import EigenlayerNetwork

@pytest.fixture
def verifier():
    network = EigenlayerNetwork()
    return Zellular(app="simple_app", network=network)

def test_get_last_finalized(verifier):
    result = verifier.get_last_finalized()
    assert result is not None
    assert "index" in result
    assert "hash" in result
    assert "chaining_hash" in result

def test_batches_stream(verifier):
    batch_stream = verifier.batches()
    batch, index = next(batch_stream)
    assert isinstance(batch, str)
    assert isinstance(index, int)
