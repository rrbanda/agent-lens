"""Pytest configuration and fixtures for Agent Lens tests.

Integration tests require a running MLflow server and seeded data.
Start MLflow: mlflow server --host 127.0.0.1 --port 5555
Seed data:    MLFLOW_TRACKING_URI=http://127.0.0.1:5555 python tests/seed_mlflow_data.py
"""

from __future__ import annotations

import json
import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires running MLflow + MCP")
    config.addinivalue_line("markers", "unit: fast tests with no external deps")


@pytest.fixture(scope="session")
def mlflow_tracking_uri():
    return os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5555")


@pytest.fixture(scope="session")
def seed_results():
    """Load seed results written by seed_mlflow_data.py."""
    path = os.path.join(
        os.path.dirname(__file__), "..", ".mlflow-test", "seed-results.json"
    )
    if not os.path.exists(path):
        pytest.skip("Seed results not found. Run: python tests/seed_mlflow_data.py")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def mcp_client(mlflow_tracking_uri):
    """Provide a connected MCP client for the test session."""
    from tests.mcp_client import MCPClient

    client = MCPClient(tracking_uri=mlflow_tracking_uri)
    try:
        client.start()
    except Exception as e:
        pytest.skip(f"Could not start MCP client: {e}")
    yield client
    client.stop()


@pytest.fixture(scope="session")
def mcp_tool_names(mcp_client):
    """Return the set of tool names available on the MCP server."""
    return mcp_client.tool_names()
