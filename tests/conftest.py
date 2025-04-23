import os
import json
from typing import Any
import logging
from uuid import uuid4

import pytest


@pytest.fixture(scope="session", autouse=True)
def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logging.getLogger("zellular").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


@pytest.fixture
def test_data_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def load_test_nodes(test_data_dir: str) -> dict[str, dict[str, Any]]:
    nodes_file = os.path.join(test_data_dir, "nodes.json")
    with open(nodes_file) as f:
        data: dict[str, dict[str, Any]] = json.load(f)
        return data


@pytest.fixture
def generate_test_tx() -> dict[str, Any]:
    return {"tx_id": str(uuid4()), "operation": "test_operation"}
