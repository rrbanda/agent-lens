"""Integration tests for Agent Lens skills against a live MLflow MCP server.

Each test class validates the MCP tool chain that a specific skill depends on.
Tests call real MCP tools via JSON-RPC and verify:
  1. Tool exists in the MCP server
  2. Tool accepts the parameters the skill implies
  3. Tool returns data the skill expects to consume

Prerequisites:
  - MLflow server running: mlflow server --host 127.0.0.1 --port 5555
  - Data seeded: MLFLOW_TRACKING_URI=http://127.0.0.1:5555 python tests/seed_mlflow_data.py
  - Run: pytest tests/test_mcp_integration.py -m integration
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.integration


class TestMCPToolDiscovery:
    """Verify the actual tools available on the MLflow MCP server."""

    def test_mcp_lists_tools(self, mcp_client):
        tools = mcp_client.list_tools()
        assert len(tools) > 0, "MCP server returned no tools"

    def test_expected_tools_exist(self, mcp_tool_names):
        """These are the tools Agent Lens skills NEED (using real MCP names)."""
        required = {
            "search_experiments",
            "get_experiment",
            "search_traces",
            "get_trace",
            "list_runs",
            "describe_run",
            "evaluate_traces",
            "list_scorers",
            "log_trace_feedback",
            "log_trace_expectation",
            "set_trace_tag",
            "delete_trace_tag",
            "get_trace_assessment",
            "update_trace_assessment",
            "delete_trace_assessment",
            "register_llm_judge_scorer",
            "link_traces_to_run",
            "delete_traces",
            "create_run",
            "create_experiment",
        }
        missing = required - mcp_tool_names
        assert not missing, f"Required tools missing from MCP: {missing}"

    def test_config_tool_name_mismatches(self, mcp_tool_names):
        """Document tool names that config.yaml gets WRONG vs actual MCP."""
        wrong_names = {
            "evaluate": "evaluate_traces",
            "log_feedback": "log_trace_feedback",
            "log_expectation": "log_trace_expectation",
            "get_assessment": "get_trace_assessment",
            "update_assessment": "update_trace_assessment",
            "delete_assessment": "delete_trace_assessment",
            "register_llm_judge": "register_llm_judge_scorer",
            "link_traces": "link_traces_to_run",
        }
        for wrong, correct in wrong_names.items():
            assert wrong not in mcp_tool_names, (
                f"'{wrong}' should NOT exist -- config.yaml uses wrong name"
            )
            assert correct in mcp_tool_names, (
                f"'{correct}' should exist as the real tool name"
            )

    def test_experiments_csv_does_not_exist(self, mcp_tool_names):
        assert "experiments_csv" not in mcp_tool_names, (
            "experiments_csv does not exist in MLflow MCP -- remove from config"
        )

    def test_no_logged_model_tools(self, mcp_tool_names):
        """Confirm LoggedModel tools are NOT in the official MCP."""
        logged_model_tools = {
            "search_logged_models",
            "get_logged_model",
            "set_logged_model_tags",
            "create_logged_model",
            "create_external_model",
            "finalize_logged_model",
            "delete_logged_model_tag",
            "log_logged_model_params",
        }
        found = logged_model_tools & mcp_tool_names
        assert not found, (
            f"LoggedModel tools should NOT be in official MCP: {found}"
        )


class TestTraceExplorerSkill:
    """Validate trace-explorer skill: search_experiments, search_traces, get_trace."""

    def test_search_experiments(self, mcp_client):
        text = mcp_client.call_tool_text("search_experiments")
        assert "customer-support-agent" in text
        assert "code-review-agent" in text
        assert "sales-assistant-agent" in text

    def test_search_traces_by_experiment(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "search_traces",
            {"experiment_id": exp_id, "max_results": 10},
        )
        assert "tr-" in text

    def test_search_traces_filter_errors(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "search_traces",
            {
                "experiment_id": exp_id,
                "filter_string": "status = 'ERROR'",
                "max_results": 50,
            },
        )
        assert "ERROR" in text or "tr-" in text

    def test_search_traces_filter_by_tag(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "search_traces",
            {
                "experiment_id": exp_id,
                "filter_string": "tags.regression = 'true'",
                "max_results": 10,
            },
        )
        assert "tr-" in text

    def test_get_trace(self, mcp_client, seed_results):
        trace_ids = seed_results["customer-support-agent"]["trace_ids"]
        assert len(trace_ids) > 0
        text = mcp_client.call_tool_text(
            "get_trace",
            {"trace_id": trace_ids[0]},
        )
        assert trace_ids[0] in text or "trace_id" in text

    def test_get_trace_with_extract_fields(self, mcp_client, seed_results):
        trace_ids = seed_results["customer-support-agent"]["trace_ids"]
        text = mcp_client.call_tool_text(
            "get_trace",
            {"trace_id": trace_ids[0], "extract_fields": "info.trace_id,info.state"},
        )
        assert trace_ids[0] in text or "OK" in text or "ERROR" in text


class TestAggregateTracesSkill:
    """Validate aggregate-traces skill: search_traces with pagination."""

    def test_search_traces_pagination(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "search_traces",
            {"experiment_id": exp_id, "max_results": 2},
        )
        assert "tr-" in text

    def test_search_traces_json_output(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "search_traces",
            {"experiment_id": exp_id, "max_results": 5, "output": "json"},
        )
        data = json.loads(text)
        assert isinstance(data, (list, dict))

    def test_search_traces_order_by(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "search_traces",
            {
                "experiment_id": exp_id,
                "max_results": 5,
                "order_by": "timestamp_ms DESC",
            },
        )
        assert "tr-" in text


class TestAnalyzeSessionSkill:
    """Validate analyze-session skill: session metadata filtering."""

    def test_get_trace_has_metadata(self, mcp_client, seed_results):
        trace_ids = seed_results["customer-support-agent"]["trace_ids"]
        text = mcp_client.call_tool_text(
            "get_trace",
            {"trace_id": trace_ids[0], "extract_fields": "info.trace_id,data.spans"},
        )
        assert "tr-" in text or "span" in text.lower()


class TestQualityDashboardSkill:
    """Validate quality-dashboard skill: fleet-wide scanning."""

    def test_search_experiments_lists_fleet(self, mcp_client):
        text = mcp_client.call_tool_text(
            "search_experiments",
            {"max_results": 20},
        )
        assert "customer-support-agent" in text

    def test_list_runs_for_experiment(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "list_runs",
            {"experiment_id": exp_id},
        )
        assert "eval-customer-support-agent" in text or "run" in text.lower()


class TestCompareEvaluationsSkill:
    """Validate compare-evaluations skill: list_runs + describe_run."""

    def test_list_runs(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "list_runs",
            {"experiment_id": exp_id},
        )
        assert "eval-" in text or "run" in text.lower()

    def test_describe_run(self, mcp_client, seed_results):
        import mlflow

        mlflow.set_tracking_uri("http://127.0.0.1:5555")
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        client = mlflow.MlflowClient()
        runs = client.search_runs([exp_id], max_results=1)
        assert len(runs) > 0
        run_id = runs[0].info.run_id

        text = mcp_client.call_tool_text(
            "describe_run",
            {"run_id": run_id},
        )
        assert run_id in text or "pass_rate" in text or "metrics" in text.lower()


class TestCreateRegressionSkill:
    """Validate create-regression skill: annotation + tagging writes."""

    def test_set_trace_tag(self, mcp_client, seed_results):
        trace_ids = seed_results["code-review-agent"]["trace_ids"]
        tid = trace_ids[-1]
        result = mcp_client.call_tool(
            "set_trace_tag",
            {"trace_id": tid, "key": "test_tag", "value": "integration_test"},
        )
        assert result is not None

    def test_log_trace_expectation(self, mcp_client, seed_results):
        trace_ids = seed_results["code-review-agent"]["trace_ids"]
        tid = trace_ids[-1]
        text = mcp_client.call_tool_text(
            "log_trace_expectation",
            {
                "trace_id": tid,
                "name": "test_expected_answer",
                "value": "The function should use a dict for O(1) lookups",
            },
        )
        assert "expectation" in text.lower() or "logged" in text.lower() or "success" in text.lower() or tid in text

    def test_log_trace_feedback(self, mcp_client, seed_results):
        trace_ids = seed_results["code-review-agent"]["trace_ids"]
        tid = trace_ids[-1]
        text = mcp_client.call_tool_text(
            "log_trace_feedback",
            {
                "trace_id": tid,
                "name": "test_quality_score",
                "value": "0.8",
                "rationale": "Good but could be more detailed",
                "source_type": "HUMAN",
                "source_id": "test@example.com",
            },
        )
        assert "feedback" in text.lower() or "logged" in text.lower() or "success" in text.lower() or tid in text

    def test_delete_trace_tag(self, mcp_client, seed_results):
        trace_ids = seed_results["code-review-agent"]["trace_ids"]
        tid = trace_ids[-1]
        mcp_client.call_tool(
            "set_trace_tag",
            {"trace_id": tid, "key": "temp_tag", "value": "to_delete"},
        )
        result = mcp_client.call_tool(
            "delete_trace_tag",
            {"trace_id": tid, "key": "temp_tag"},
        )
        assert result is not None


class TestReviewTraceSkill:
    """Validate review-trace skill: full assessment CRUD + tag lifecycle."""

    def test_get_trace_full_detail(self, mcp_client, seed_results):
        trace_ids = seed_results["customer-support-agent"]["trace_ids"]
        text = mcp_client.call_tool_text(
            "get_trace",
            {"trace_id": trace_ids[0]},
        )
        assert trace_ids[0] in text or "span" in text.lower()

    def test_get_trace_assessment(self, mcp_client, seed_results):
        import mlflow

        mlflow.set_tracking_uri("http://127.0.0.1:5555")
        trace_ids = seed_results["customer-support-agent"]["trace_ids"]
        tid = trace_ids[0]
        trace = mlflow.MlflowClient().get_trace(tid)
        assessments = trace.info.assessments or []
        if not assessments:
            pytest.skip("No assessments on trace")

        asmt_id = assessments[0].assessment_id
        text = mcp_client.call_tool_text(
            "get_trace_assessment",
            {"trace_id": tid, "assessment_id": asmt_id},
        )
        assert asmt_id in text or "assessment" in text.lower()

    def test_update_trace_assessment(self, mcp_client, seed_results):
        import mlflow

        mlflow.set_tracking_uri("http://127.0.0.1:5555")
        trace_ids = seed_results["customer-support-agent"]["trace_ids"]
        tid = trace_ids[0]

        asmt = mlflow.log_feedback(
            trace_id=tid,
            name="update_test",
            value=0.5,
            rationale="Initial value",
        )

        text = mcp_client.call_tool_text(
            "update_trace_assessment",
            {
                "trace_id": tid,
                "assessment_id": asmt.assessment_id,
                "value": "0.9",
                "rationale": "Updated after review",
            },
        )
        assert "update" in text.lower() or asmt.assessment_id in text or "success" in text.lower()

    def test_delete_trace_assessment(self, mcp_client, seed_results):
        import mlflow

        mlflow.set_tracking_uri("http://127.0.0.1:5555")
        trace_ids = seed_results["customer-support-agent"]["trace_ids"]
        tid = trace_ids[0]

        asmt = mlflow.log_feedback(
            trace_id=tid,
            name="delete_test",
            value=0.1,
            rationale="Will be deleted",
        )

        result = mcp_client.call_tool(
            "delete_trace_assessment",
            {"trace_id": tid, "assessment_id": asmt.assessment_id},
        )
        assert result is not None

    def test_tag_lifecycle(self, mcp_client, seed_results):
        trace_ids = seed_results["sales-assistant-agent"]["trace_ids"]
        tid = trace_ids[-1]

        mcp_client.call_tool("set_trace_tag", {
            "trace_id": tid, "key": "needs_fix", "value": "true",
        })
        mcp_client.call_tool("set_trace_tag", {
            "trace_id": tid, "key": "reviewed", "value": "true",
        })

        text = mcp_client.call_tool_text("get_trace", {"trace_id": tid})
        assert "needs_fix" in text or "reviewed" in text

        mcp_client.call_tool("delete_trace_tag", {
            "trace_id": tid, "key": "needs_fix",
        })


class TestEvaluateAgentSkill:
    """Validate evaluate-agent skill (partial -- core eval, no LoggedModel)."""

    def test_list_scorers_builtin(self, mcp_client):
        text = mcp_client.call_tool_text(
            "list_scorers",
            {"builtin": "true"},
        )
        assert "Correctness" in text or "Safety" in text or "RelevanceToQuery" in text or "scorer" in text.lower()

    def test_list_scorers_for_experiment(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "list_scorers",
            {"experiment_id": exp_id},
        )
        assert text is not None

    def test_create_run(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        text = mcp_client.call_tool_text(
            "create_run",
            {
                "experiment_id": exp_id,
                "run_name": "test-eval-run",
                "tags": ["profile=chat", "test=true"],
                "status": "FINISHED",
            },
        )
        assert "run" in text.lower() or "test-eval-run" in text

    def test_link_traces_to_run(self, mcp_client, seed_results):
        import mlflow

        mlflow.set_tracking_uri("http://127.0.0.1:5555")
        exp_id = seed_results["customer-support-agent"]["experiment_id"]

        with mlflow.start_run(experiment_id=exp_id, run_name="link-test-run"):
            run_id = mlflow.active_run().info.run_id

        trace_ids = seed_results["customer-support-agent"]["trace_ids"][:2]
        text = mcp_client.call_tool_text(
            "link_traces_to_run",
            {"run_id": run_id, "trace_ids": trace_ids},
        )
        assert "link" in text.lower() or "success" in text.lower() or run_id in text


class TestEvaluateTracesTool:
    """Test the evaluate_traces MCP tool specifically (requires LLM judge)."""

    def test_evaluate_traces_tool_exists(self, mcp_tool_names):
        assert "evaluate_traces" in mcp_tool_names

    @pytest.mark.skip(reason="evaluate_traces requires an LLM judge endpoint -- skip in CI")
    def test_evaluate_traces_call(self, mcp_client, seed_results):
        exp_id = seed_results["customer-support-agent"]["experiment_id"]
        trace_ids = seed_results["customer-support-agent"]["trace_ids"][:2]
        text = mcp_client.call_tool_text(
            "evaluate_traces",
            {
                "experiment_id": exp_id,
                "trace_ids": ",".join(trace_ids),
                "scorers": "Safety",
            },
        )
        assert "score" in text.lower() or "result" in text.lower()
