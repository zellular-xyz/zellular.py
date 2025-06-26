from typing import Any
import logging

import pytest
from zellular.zellular import Zellular, ZellularAsync
from zellular.networks.static import StaticNetwork

logger = logging.getLogger(__name__)


@pytest.fixture
def verifier(load_test_nodes: dict[str, dict[str, Any]]) -> Zellular:
    network = StaticNetwork(load_test_nodes, threshold_percent=30)
    return Zellular(app="simple_app", network=network)


@pytest.fixture
def verifier_async(load_test_nodes: dict[str, dict[str, Any]]) -> ZellularAsync:
    network = StaticNetwork(load_test_nodes, threshold_percent=30)
    return ZellularAsync(app="simple_app", network=network)


def test_blocking_send(verifier: Zellular, generate_test_tx: str) -> None:
    index = verifier.send(generate_test_tx, blocking=True)
    logger.info(f"The sent batch sequenced at {index}")
    assert index is not None and index > 0


@pytest.mark.asyncio
async def test_blocking_send_async(verifier_async: ZellularAsync, generate_test_tx: str) -> None:
    index = await verifier_async.send(generate_test_tx, blocking=True)
    logger.info(f"The sent batch sequenced at {index}")
    assert index is not None and index > 0
