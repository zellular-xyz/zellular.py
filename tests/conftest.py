"""Common test fixtures and utilities for testing the zellular package."""

import os
import json
from typing import Any
import logging

import pytest

# Configure logging for tests
@pytest.fixture(scope="session", autouse=True)
def configure_logging() -> None:
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

@pytest.fixture
def test_data_dir() -> str:
    """Return the path to the test data directory."""
    return os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def load_test_nodes(test_data_dir: str) -> dict[str, dict[str, Any]]:
    """Load test node data from nodes.json file."""
    nodes_file = os.path.join(test_data_dir, "nodes.json")
    with open(nodes_file) as f:
        data: dict[str, dict[str, Any]] = json.load(f)
        return data

@pytest.fixture
def generate_test_tx() -> dict[str, Any]:
    """Generate a test transaction with random UUID."""
    from uuid import uuid4
    return {"tx_id": str(uuid4()), "operation": "test_operation"} 