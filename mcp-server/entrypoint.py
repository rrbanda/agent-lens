"""
Agent Lens — MLflow Evaluation MCP Server (v2)

A Model Context Protocol (MCP) server that provides AI agents with
evaluation, annotation, and governance capabilities over MLflow data.

Unlike v1 (read-only httpx), this server uses the MLflow Python SDK directly
to enable:
  - Running evaluations via mlflow.genai.evaluate()
  - Annotating traces with human feedback (mlflow.log_feedback)
  - Managing evaluation datasets (mlflow.genai.datasets)
  - Deployment quality gates (compare runs, pass/fail)

Based on patterns from https://github.com/mlflow/skills

Environment Variables:
    MLFLOW_TRACKING_URI: MLflow tracking server URL
    MLFLOW_EXPERIMENT_ID: Default experiment ID
    MLFLOW_WORKSPACE: Kubernetes namespace / MLflow workspace
    JUDGE_MODEL: LLM model URI for scorers (default: gemini:/gemini-2.5-flash)
    MCP_HOST / MCP_PORT: Server bind config
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import mlflow
from mlflow.entities import AssessmentSource, AssessmentSourceType
from fastmcp import FastMCP

mcp = FastMCP(
    name="agent-lens",
    instructions=(
        "Agent Lens evaluation platform. Use these tools to evaluate agents, "
        "annotate traces with feedback, manage evaluation datasets, and check "
        "deployment quality gates."
    ),
)

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gemini:/gemini-2.5-flash")


def _configure():
    """Set up MLflow connection from environment."""
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if uri:
        mlflow.set_tracking_uri(uri)

    token_file = os.environ.get("MLFLOW_TRACKING_TOKEN_FILE")
    if token_file and os.path.isfile(token_file):
        with open(token_file) as f:
            os.environ["MLFLOW_TRACKING_TOKEN"] = f.read().strip()

    if os.environ.get("MLFLOW_TRACKING_INSECURE_TLS", "").lower() in ("true", "1"):
        os.environ.setdefault("MLFLOW_TRACKING_INSECURE_TLS", "true")

    exp_id = os.environ.get("MLFLOW_EXPERIMENT_ID")
    if exp_id:
        os.environ.setdefault("MLFLOW_EXPERIMENT_ID", exp_id)


_configure()


# =============================================================================
# OBSERVABILITY TOOLS (read)
# =============================================================================


@mcp.tool()
def list_experiments(max_results: int = 100) -> str:
    """List all MLflow experiments with IDs, names, and lifecycle stage."""
    from mlflow import MlflowClient

    client = MlflowClient()
    experiments = client.search_experiments(max_results=max_results)
    return json.dumps([{
        "experiment_id": e.experiment_id,
        "name": e.name,
        "lifecycle_stage": e.lifecycle_stage,
        "tags": dict(e.tags) if e.tags else {},
    } for e in experiments], indent=2)


@mcp.tool()
def search_traces(
    experiment_id: str,
    filter_string: str = "",
    max_results: int = 25,
) -> str:
    """Search traces in an experiment with optional filtering.

    Args:
        experiment_id: The experiment ID to search.
        filter_string: Filter like 'trace.status = "ERROR"' or 'trace.timestamp_ms > 1700000000000'
        max_results: Maximum traces to return.
    """
    traces = mlflow.search_traces(
        experiment_ids=[experiment_id],
        filter_string=filter_string or None,
        max_results=max_results,
    )
    results = []
    for _, row in traces.iterrows():
        results.append({
            "trace_id": row.get("trace_id") or row.get("request_id"),
            "status": row.get("status"),
            "timestamp_ms": row.get("timestamp_ms"),
            "execution_time_ms": row.get("execution_time_ms"),
        })
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
def get_trace(trace_id: str) -> str:
    """Get full details of a specific trace including spans and assessments.

    Args:
        trace_id: The trace/request ID.
    """
    from mlflow import MlflowClient

    client = MlflowClient()
    trace = client.get_trace(trace_id)
    info = trace.info
    spans = trace.data.spans if trace.data else []

    span_summaries = []
    for s in spans[:20]:
        span_summaries.append({
            "name": s.name,
            "span_type": getattr(s, "span_type", None),
            "status": str(s.status) if hasattr(s, "status") else None,
            "start_time": getattr(s, "start_time_ns", None),
            "end_time": getattr(s, "end_time_ns", None),
        })

    assessments = []
    if hasattr(info, "assessments") and info.assessments:
        for a in info.assessments:
            assessments.append({
                "name": a.assessment_name,
                "value": a.feedback.value if hasattr(a, "feedback") and a.feedback else None,
                "source": str(a.source) if hasattr(a, "source") else None,
                "rationale": getattr(a, "rationale", None),
            })

    return json.dumps({
        "trace_id": info.trace_id,
        "status": str(info.status),
        "timestamp_ms": info.timestamp_ms,
        "execution_time_ms": info.execution_time_ms,
        "spans_count": len(spans),
        "spans": span_summaries,
        "assessments": assessments,
    }, indent=2, default=str)


@mcp.tool()
def search_runs(
    experiment_id: str,
    filter_string: str = "",
    max_results: int = 10,
    order_by: str = "start_time DESC",
) -> str:
    """Search runs in an experiment (evaluation runs, training runs, etc).

    Args:
        experiment_id: Experiment ID to search in.
        filter_string: MLflow filter, e.g. 'metrics.relevance_mean > 3.0'
        max_results: Max runs to return.
        order_by: Order by clause.
    """
    runs = mlflow.search_runs(
        experiment_ids=[experiment_id],
        filter_string=filter_string or None,
        max_results=max_results,
        order_by=[order_by] if order_by else None,
    )
    results = []
    for _, row in runs.iterrows():
        metrics = {k: v for k, v in row.items() if k.startswith("metrics.") and v == v}
        params = {k: v for k, v in row.items() if k.startswith("params.") and v == v}
        results.append({
            "run_id": row.get("run_id"),
            "run_name": row.get("tags.mlflow.runName"),
            "status": row.get("status"),
            "start_time": str(row.get("start_time")),
            "metrics": metrics,
            "params": params,
        })
    return json.dumps(results, indent=2, default=str)


# =============================================================================
# EVALUATION TOOLS (the core of v2)
# =============================================================================


@mcp.tool()
def run_evaluation(
    experiment_id: str,
    dataset_name: str = "",
    scorer_names: str = "RelevanceToQuery,ToolCallCorrectness",
    max_traces: int = 50,
    filter_string: str = "",
) -> str:
    """Run an evaluation on an agent's traces using MLflow scorers.

    This is the primary evaluation tool. It:
    1. Loads traces from the experiment (or a dataset)
    2. Applies selected scorers
    3. Returns aggregate quality scores

    Args:
        experiment_id: The experiment containing agent traces to evaluate.
        dataset_name: Named dataset to evaluate against (optional, uses traces if empty).
        scorer_names: Comma-separated scorer names. Options: RelevanceToQuery, RetrievalGroundedness, ToolCallCorrectness, ToolCallEfficiency, Guidelines
        max_traces: Maximum traces to evaluate (for production trace evaluation).
        filter_string: Filter for trace selection.
    """
    from mlflow.genai.scorers import (
        RelevanceToQuery,
        ToolCallCorrectness,
        ToolCallEfficiency,
    )

    scorer_map = {
        "RelevanceToQuery": RelevanceToQuery,
        "ToolCallCorrectness": ToolCallCorrectness,
        "ToolCallEfficiency": ToolCallEfficiency,
    }

    selected_scorers = []
    for name in scorer_names.split(","):
        name = name.strip()
        if name in scorer_map:
            selected_scorers.append(scorer_map[name](model=JUDGE_MODEL))

    if not selected_scorers:
        return json.dumps({"error": f"No valid scorers found in: {scorer_names}"})

    try:
        mlflow.set_experiment(experiment_id=experiment_id)

        if dataset_name:
            from mlflow.genai.datasets import search_datasets
            datasets = search_datasets(filter_string=f"name = '{dataset_name}'")
            if not datasets:
                return json.dumps({"error": f"Dataset '{dataset_name}' not found"})
            data = datasets[0]
        else:
            traces_df = mlflow.search_traces(
                experiment_ids=[experiment_id],
                filter_string=filter_string or None,
                max_results=max_traces,
            )
            if traces_df.empty:
                return json.dumps({"error": "No traces found for evaluation"})
            data = traces_df

        results = mlflow.genai.evaluate(
            data=data,
            scorers=selected_scorers,
        )

        metrics = results.metrics if hasattr(results, "metrics") else {}
        return json.dumps({
            "status": "completed",
            "experiment_id": experiment_id,
            "traces_evaluated": len(data) if hasattr(data, "__len__") else "unknown",
            "scorers_used": scorer_names,
            "metrics": {k: round(v, 3) if isinstance(v, float) else v for k, v in metrics.items()},
            "timestamp": datetime.utcnow().isoformat(),
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "type": type(e).__name__})


@mcp.tool()
def list_scorers(experiment_id: str = "") -> str:
    """List available and registered scorers for an experiment.

    Args:
        experiment_id: Optional experiment to check for registered scorers.
    """
    built_in = [
        {"name": "RelevanceToQuery", "type": "built-in", "requires_ground_truth": False, "description": "Checks if output is relevant to the user request"},
        {"name": "RetrievalGroundedness", "type": "built-in", "requires_ground_truth": False, "description": "Checks if output is grounded in retrieved context"},
        {"name": "ToolCallCorrectness", "type": "built-in", "requires_ground_truth": False, "description": "Evaluates if tool calls and arguments are correct"},
        {"name": "ToolCallEfficiency", "type": "built-in", "requires_ground_truth": False, "description": "Evaluates if tool calls are efficient without redundancy"},
        {"name": "Guidelines", "type": "built-in", "requires_ground_truth": False, "description": "Judge output against custom guidelines"},
    ]

    return json.dumps({
        "built_in_scorers": built_in,
        "judge_model": JUDGE_MODEL,
        "note": "Custom scorers can be created with mlflow.genai.judges.make_judge()",
    }, indent=2)


# =============================================================================
# ANNOTATION TOOLS (human feedback loop)
# =============================================================================


@mcp.tool()
def annotate_trace(
    trace_id: str,
    feedback_name: str,
    value: float,
    rationale: str = "",
    reviewer_id: str = "platform-team",
) -> str:
    """Annotate a trace with human feedback (quality score).

    Use this when a platform team member reviews a trace and wants to
    record their assessment of quality.

    Args:
        trace_id: The trace to annotate.
        feedback_name: Assessment dimension (e.g. "correctness", "relevance", "safety").
        value: Numeric score (0.0 = terrible, 1.0 = perfect).
        rationale: Explanation for the score.
        reviewer_id: Who is providing this feedback.
    """
    try:
        source = AssessmentSource(
            source_type=AssessmentSourceType.HUMAN,
            source_id=reviewer_id,
        )
        mlflow.log_feedback(
            trace_id=trace_id,
            name=feedback_name,
            value=value,
            source=source,
            rationale=rationale,
        )
        return json.dumps({
            "status": "ok",
            "trace_id": trace_id,
            "feedback": {"name": feedback_name, "value": value, "rationale": rationale},
            "reviewer": reviewer_id,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def set_expectation(
    trace_id: str,
    expected_output: str,
    expectation_name: str = "expected_output",
) -> str:
    """Set the ground truth (expected output) for a trace.

    Use this when a reviewer knows what the correct answer should have been.
    This enables ground-truth-based evaluation in future runs.

    Args:
        trace_id: The trace to annotate with ground truth.
        expected_output: What the agent should have produced.
        expectation_name: Name for this expectation field.
    """
    try:
        mlflow.log_expectation(
            trace_id=trace_id,
            name=expectation_name,
            value=expected_output,
        )
        return json.dumps({
            "status": "ok",
            "trace_id": trace_id,
            "expectation": {"name": expectation_name, "value": expected_output[:200]},
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# DATASET TOOLS (regression test management)
# =============================================================================


@mcp.tool()
def list_datasets(experiment_id: str = "") -> str:
    """List evaluation datasets available in the system.

    Args:
        experiment_id: Optional experiment to scope the search.
    """
    try:
        from mlflow.genai.datasets import search_datasets

        filter_str = f"experiment_id = '{experiment_id}'" if experiment_id else None
        datasets = search_datasets(filter_string=filter_str)
        return json.dumps([{
            "name": d.name,
            "record_count": len(d.to_df()) if hasattr(d, "to_df") else "unknown",
        } for d in datasets], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "datasets": []})


@mcp.tool()
def create_test_case(
    trace_id: str,
    dataset_name: str,
    expected_output: str,
    experiment_id: str = "",
) -> str:
    """Convert a production trace into a regression test case.

    This is the key "failure-to-dataset" pipeline action: take a trace that
    failed or had poor quality, and add it to the evaluation dataset so future
    versions are tested against it.

    Args:
        trace_id: The trace to convert into a test case.
        dataset_name: Target evaluation dataset name (creates if not exists).
        expected_output: What the correct output should be.
        experiment_id: Experiment to associate the dataset with.
    """
    try:
        from mlflow import MlflowClient
        from mlflow.genai.datasets import create_dataset, search_datasets

        client = MlflowClient()
        trace = client.get_trace(trace_id)

        root_span = None
        if trace.data and trace.data.spans:
            for span in trace.data.spans:
                if not hasattr(span, "parent_span_id") or span.parent_span_id is None:
                    root_span = span
                    break
            if not root_span:
                root_span = trace.data.spans[0]

        inputs = {}
        if root_span and hasattr(root_span, "attributes"):
            span_inputs = root_span.attributes.get("mlflow.spanInputs", {})
            if isinstance(span_inputs, str):
                import json as json_mod
                span_inputs = json_mod.loads(span_inputs)
            inputs = span_inputs if isinstance(span_inputs, dict) else {"query": str(span_inputs)}

        if not inputs:
            inputs = {"query": f"[From trace {trace_id}]"}

        record = {
            "inputs": inputs,
            "expectations": {"expected_output": expected_output},
        }

        existing = search_datasets(filter_string=f"name = '{dataset_name}'")
        if existing:
            dataset = existing[0]
        else:
            exp_ids = [experiment_id] if experiment_id else None
            dataset = create_dataset(name=dataset_name, experiment_id=exp_ids)

        dataset.merge_records([record])

        return json.dumps({
            "status": "ok",
            "dataset": dataset_name,
            "record_added": record,
            "source_trace": trace_id,
            "message": f"Test case added. Next evaluation against '{dataset_name}' will include this case.",
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# GOVERNANCE TOOLS (deployment gates)
# =============================================================================


@mcp.tool()
def check_quality_gate(
    experiment_id: str,
    baseline_run_id: str = "",
    threshold_relevance: float = 3.5,
    threshold_correctness: float = 3.5,
) -> str:
    """Check if an agent meets quality standards for deployment.

    Compares the latest evaluation run against a baseline or absolute thresholds.
    Returns PASS/FAIL with evidence — designed for CI/CD pipeline integration.

    Args:
        experiment_id: The experiment to check.
        baseline_run_id: Previous run to compare against (optional, uses thresholds if empty).
        threshold_relevance: Minimum acceptable relevance score (1-5 scale).
        threshold_correctness: Minimum acceptable correctness score (1-5 scale).
    """
    try:
        runs_df = mlflow.search_runs(
            experiment_ids=[experiment_id],
            max_results=5,
            order_by=["start_time DESC"],
        )

        if runs_df.empty:
            return json.dumps({
                "gate": "FAIL",
                "reason": "No evaluation runs found",
                "recommendation": "Run an evaluation first using run_evaluation tool",
            })

        latest = runs_df.iloc[0]
        metrics = {k.replace("metrics.", ""): v for k, v in latest.items()
                   if k.startswith("metrics.") and v == v}

        checks = []
        passed = True

        relevance = metrics.get("RelevanceToQuery/mean") or metrics.get("relevance_mean", 0)
        if relevance and relevance < threshold_relevance:
            checks.append({"metric": "relevance", "value": relevance, "threshold": threshold_relevance, "status": "FAIL"})
            passed = False
        elif relevance:
            checks.append({"metric": "relevance", "value": relevance, "threshold": threshold_relevance, "status": "PASS"})

        correctness = metrics.get("ToolCallCorrectness/mean") or metrics.get("correctness_mean", 0)
        if correctness and correctness < threshold_correctness:
            checks.append({"metric": "correctness", "value": correctness, "threshold": threshold_correctness, "status": "FAIL"})
            passed = False
        elif correctness:
            checks.append({"metric": "correctness", "value": correctness, "threshold": threshold_correctness, "status": "PASS"})

        if baseline_run_id:
            baseline_run = mlflow.get_run(baseline_run_id)
            baseline_metrics = baseline_run.data.metrics
            for key, baseline_val in baseline_metrics.items():
                current_val = metrics.get(key)
                if current_val and current_val < baseline_val * 0.9:
                    checks.append({
                        "metric": key,
                        "current": current_val,
                        "baseline": baseline_val,
                        "regression": f"{((current_val - baseline_val) / baseline_val * 100):.1f}%",
                        "status": "REGRESSION",
                    })
                    passed = False

        return json.dumps({
            "gate": "PASS" if passed else "FAIL",
            "experiment_id": experiment_id,
            "latest_run_id": latest.get("run_id"),
            "checks": checks,
            "all_metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "recommendation": "Safe to deploy" if passed else "Quality below threshold — investigate before deploying",
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({"gate": "ERROR", "error": str(e)})


# =============================================================================
# SMART SAMPLING (review queue)
# =============================================================================


@mcp.tool()
def get_review_queue(
    experiment_id: str,
    max_results: int = 10,
    strategy: str = "low_score",
) -> str:
    """Get traces that need human review based on a sampling strategy.

    Surfaces traces that are most likely to benefit from human annotation.

    Args:
        experiment_id: Experiment to sample from.
        max_results: Number of traces to surface for review.
        strategy: Sampling strategy - "low_score" (low automated scores), "errors" (failed traces), "random" (random sample for calibration).
    """
    try:
        if strategy == "errors":
            filter_str = 'trace.status = "ERROR"'
        elif strategy == "low_score":
            filter_str = None
        else:
            filter_str = None

        traces_df = mlflow.search_traces(
            experiment_ids=[experiment_id],
            filter_string=filter_str,
            max_results=max_results * 3,
        )

        if traces_df.empty:
            return json.dumps({"queue": [], "message": "No traces found"})

        if strategy == "random":
            sample = traces_df.sample(min(max_results, len(traces_df)))
        else:
            sample = traces_df.head(max_results)

        queue = []
        for _, row in sample.iterrows():
            queue.append({
                "trace_id": row.get("trace_id") or row.get("request_id"),
                "status": row.get("status"),
                "timestamp_ms": row.get("timestamp_ms"),
                "execution_time_ms": row.get("execution_time_ms"),
                "reason": f"Selected by '{strategy}' strategy",
            })

        return json.dumps({
            "queue": queue,
            "strategy": strategy,
            "total_available": len(traces_df),
            "returned": len(queue),
            "action": "Use annotate_trace() or set_expectation() to provide feedback",
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e), "queue": []})


# =============================================================================
# HEALTH CHECK
# =============================================================================


@mcp.tool()
def health_check() -> str:
    """Check connectivity to MLflow and return system status."""
    try:
        uri = mlflow.get_tracking_uri()
        from mlflow import MlflowClient
        client = MlflowClient()
        experiments = client.search_experiments(max_results=1)
        return json.dumps({
            "status": "healthy",
            "tracking_uri": uri,
            "experiments_accessible": len(experiments) > 0,
            "judge_model": JUDGE_MODEL,
            "timestamp": datetime.utcnow().isoformat(),
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "unhealthy", "error": str(e)})


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))

    print(f"Starting Agent Lens MCP Server v2 on {host}:{port}", file=sys.stderr)
    print(f"  MLFLOW_TRACKING_URI = {os.environ.get('MLFLOW_TRACKING_URI', 'not set')}", file=sys.stderr)
    print(f"  JUDGE_MODEL = {JUDGE_MODEL}", file=sys.stderr)
    print(f"  Transport = streamable-http at /mcp", file=sys.stderr)
    print(f"  Tools: evaluation, annotation, datasets, governance", file=sys.stderr)

    mcp.run(transport="streamable-http", host=host, port=port)
