"""Unit tests for Agent Lens MCP server tools.

Tests each tool's happy path and error handling with mocked MLflow client.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")
os.environ.setdefault("JUDGE_MODEL", "test-model")


@pytest.fixture(autouse=True)
def mock_mlflow_client():
    """Patch the singleton MlflowClient for all tests."""
    with patch("entrypoint._mlflow_client") as mock_client:
        with patch("entrypoint._get_client", return_value=mock_client):
            yield mock_client


@pytest.fixture(autouse=True)
def disable_timeout():
    """Disable SIGALRM-based timeouts in tests."""
    with patch("entrypoint.with_timeout", lambda *a, **kw: lambda f: f):
        yield


class TestListExperiments:
    def test_returns_experiments(self, mock_mlflow_client):
        from entrypoint import list_experiments

        mock_exp = MagicMock()
        mock_exp.experiment_id = "1"
        mock_exp.name = "test-agent"
        mock_exp.lifecycle_stage = "active"
        mock_exp.tags = {"team": "platform"}
        mock_mlflow_client.search_experiments.return_value = [mock_exp]

        result = json.loads(list_experiments(max_results=10))
        assert len(result) == 1
        assert result[0]["experiment_id"] == "1"
        assert result[0]["name"] == "test-agent"

    def test_empty_result(self, mock_mlflow_client):
        from entrypoint import list_experiments

        mock_mlflow_client.search_experiments.return_value = []
        result = json.loads(list_experiments())
        assert result == []


class TestSearchTraces:
    @patch("entrypoint.mlflow")
    def test_returns_traces(self, mock_mlflow_mod, mock_mlflow_client):
        import pandas as pd
        from entrypoint import search_traces

        df = pd.DataFrame([{
            "trace_id": "tr-001",
            "status": "OK",
            "timestamp_ms": 1700000000000,
            "execution_time_ms": 250,
        }])
        mock_mlflow_mod.search_traces.return_value = df

        result = json.loads(search_traces(experiment_id="1", max_results=10))
        assert len(result) == 1
        assert result[0]["trace_id"] == "tr-001"
        assert result[0]["status"] == "OK"


class TestGetTrace:
    def test_returns_trace_details(self, mock_mlflow_client):
        from entrypoint import get_trace

        mock_trace = MagicMock()
        mock_trace.info.trace_id = "tr-001"
        mock_trace.info.status = "OK"
        mock_trace.info.experiment_id = "1"
        mock_trace.info.timestamp_ms = 1700000000000
        mock_trace.info.execution_time_ms = 250
        mock_trace.info.assessments = []
        mock_trace.data.spans = []
        mock_mlflow_client.get_trace.return_value = mock_trace

        result = json.loads(get_trace("tr-001"))
        assert result["trace_id"] == "tr-001"


class TestAnnotateTrace:
    @patch("entrypoint.mlflow")
    def test_logs_feedback(self, mock_mlflow_mod, mock_mlflow_client):
        from entrypoint import annotate_trace

        mock_mlflow_mod.log_feedback.return_value = None

        result = json.loads(annotate_trace(
            trace_id="tr-001",
            feedback_name="quality",
            value="4",
            rationale="Good response",
        ))
        assert result["status"] == "ok"
        mock_mlflow_mod.log_feedback.assert_called_once()


class TestCheckQualityGate:
    @patch("entrypoint.mlflow")
    def test_passes_quality_gate(self, mock_mlflow_mod, mock_mlflow_client):
        import pandas as pd
        from entrypoint import check_quality_gate

        runs_df = pd.DataFrame([{
            "run_id": "run-1",
            "metrics.relevance_mean": 4.5,
            "metrics.correctness_mean": 4.8,
            "start_time": "2025-01-01",
            "status": "FINISHED",
        }])
        mock_mlflow_mod.search_runs.return_value = runs_df

        result = json.loads(check_quality_gate(
            experiment_id="1",
            threshold=4.0,
        ))
        assert result["decision"] in ("PASS", "FAIL", "NO_DATA")


class TestHealthCheck:
    def test_healthy(self, mock_mlflow_client):
        from entrypoint import health_check

        mock_exp = MagicMock()
        mock_mlflow_client.search_experiments.return_value = [mock_exp]

        with patch("entrypoint.mlflow") as mock_mod:
            mock_mod.get_tracking_uri.return_value = "http://localhost:5000"
            result = json.loads(health_check())
            assert result["status"] == "healthy"

    def test_unhealthy(self, mock_mlflow_client):
        from entrypoint import health_check

        mock_mlflow_client.search_experiments.side_effect = Exception("Connection refused")

        with patch("entrypoint.mlflow") as mock_mod:
            mock_mod.get_tracking_uri.return_value = "http://localhost:5000"
            result = json.loads(health_check())
            assert result["status"] == "unhealthy"


class TestListScorers:
    def test_returns_scorer_list(self, mock_mlflow_client):
        from entrypoint import list_scorers

        result = json.loads(list_scorers())
        assert "available_scorers" in result
        scorers = result["available_scorers"]
        scorer_names = [s["name"] for s in scorers]
        assert "RelevanceToQuery" in scorer_names
        assert "RetrievalGroundedness" in scorer_names
        assert "Guidelines" in scorer_names
        assert "ToolCallCorrectness" in scorer_names
        assert "ToolCallEfficiency" in scorer_names
