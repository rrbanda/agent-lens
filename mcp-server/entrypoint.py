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

DEFAULT_TIMEOUT = 30
EVAL_TIMEOUT = 120
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5


def _configure():
    """Set up MLflow connection from environment."""
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if uri:
        mlflow.set_tracking_uri(uri)

    token_file = os.environ.get("MLFLOW_TRACKING_TOKEN_FILE")
    if token_file and os.path.isfile(token_file):
        with open(token_file) as f:
            os.environ["MLFLOW_TRACKING_TOKEN"] = f.read().strip()

    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE")
    if ca_bundle and os.path.isfile(ca_bundle):
        os.environ.setdefault("CURL_CA_BUNDLE", ca_bundle)

    exp_id = os.environ.get("MLFLOW_EXPERIMENT_ID")
    if exp_id:
        os.environ.setdefault("MLFLOW_EXPERIMENT_ID", exp_id)


_configure()


import functools
import signal
import time


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("MLflow operation timed out")


def with_timeout(timeout_seconds: int = DEFAULT_TIMEOUT):
    """Decorator to apply a timeout to a function."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout_seconds)
            try:
                return func(*args, **kwargs)
            except TimeoutError:
                return json.dumps({"error": f"Operation timed out after {timeout_seconds}s"})
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        return wrapper
    return decorator


def with_retry(max_retries: int = MAX_RETRIES, backoff: float = RETRY_BACKOFF):
    """Decorator to retry transient MLflow failures with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except TimeoutError:
                    raise
                except Exception as e:
                    last_err = e
                    err_str = str(e).lower()
                    transient = any(k in err_str for k in [
                        "connection", "timeout", "503", "502", "429", "unavailable",
                    ])
                    if not transient or attempt == max_retries - 1:
                        return json.dumps({"error": str(e)})
                    time.sleep(backoff ** attempt)
            return json.dumps({"error": str(last_err)})
        return wrapper
    return decorator


def _get_client():
    """Return the module-level singleton MlflowClient."""
    return _mlflow_client


from mlflow import MlflowClient
_mlflow_client = MlflowClient()


# =============================================================================
# OBSERVABILITY TOOLS (read)
# =============================================================================


@mcp.tool()
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
def list_experiments(max_results: int = 100) -> str:
    """List all MLflow experiments with IDs, names, and lifecycle stage."""
    client = _get_client()
    experiments = client.search_experiments(max_results=max_results)
    return json.dumps([{
        "experiment_id": e.experiment_id,
        "name": e.name,
        "lifecycle_stage": e.lifecycle_stage,
        "tags": dict(e.tags) if e.tags else {},
    } for e in experiments], indent=2)


@mcp.tool()
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
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
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
def get_trace(trace_id: str) -> str:
    """Get full details of a specific trace including spans and assessments.

    Args:
        trace_id: The trace/request ID.
    """
    client = _get_client()
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
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
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
@with_timeout(EVAL_TIMEOUT)
@with_retry(max_retries=2)
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
        Guidelines,
        RelevanceToQuery,
        RetrievalGroundedness,
        ToolCallCorrectness,
        ToolCallEfficiency,
    )

    scorer_map = {
        "RelevanceToQuery": RelevanceToQuery,
        "RetrievalGroundedness": RetrievalGroundedness,
        "ToolCallCorrectness": ToolCallCorrectness,
        "ToolCallEfficiency": ToolCallEfficiency,
        "Guidelines": Guidelines,
    }

    selected_scorers = []
    for name in scorer_names.split(","):
        name = name.strip()
        if name in scorer_map:
            if name == "Guidelines":
                selected_scorers.append(scorer_map[name](
                    model=JUDGE_MODEL,
                    guidelines="The agent response must be helpful, accurate, and safe.",
                ))
            else:
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
@with_timeout(DEFAULT_TIMEOUT)
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
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
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
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
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
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
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
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
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
        from mlflow.genai.datasets import create_dataset, search_datasets

        client = _get_client()
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
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
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
# FLEET HEALTH SUMMARY (quality dashboard)
# =============================================================================

SUMMARY_TIMEOUT = 60
MAX_SUMMARY_EXPERIMENTS = 20


def _extract_quality_score(metrics: dict) -> float | None:
    """Pick a representative quality score from run metrics (1-5 scale preferred)."""
    for key in (
        "RelevanceToQuery/mean",
        "relevance_mean",
        "ToolCallCorrectness/mean",
        "correctness_mean",
        "Guidelines/mean",
    ):
        val = metrics.get(key)
        if val is not None and val == val:  # not NaN
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    for key, val in metrics.items():
        if key.endswith("/mean") or key.endswith("_mean"):
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def _classify_health(
    trace_count: int,
    error_rate: float | None,
    quality_score: float | None,
) -> str:
    """Classify experiment health using quality-dashboard skill thresholds."""
    if trace_count == 0:
        return "INACTIVE"
    er = error_rate if error_rate is not None else 0.0
    qs = quality_score
    if er > 15 or (qs is not None and qs < 3.0):
        return "CRITICAL"
    if er >= 5 or (qs is not None and qs < 4.0):
        return "WARNING"
    if qs is None and er < 5:
        # Active with low errors but no eval yet — treat as WARNING so ops notice
        return "WARNING"
    return "HEALTHY"


def _summarize_one_experiment(experiment_id: str, name: str, max_traces: int) -> dict:
    """Aggregate traces + latest run metrics for a single experiment."""
    traces_df = mlflow.search_traces(
        experiment_ids=[experiment_id],
        max_results=max_traces,
    )
    trace_count = 0 if traces_df is None or traces_df.empty else len(traces_df)
    error_rate = None
    avg_latency_ms = None

    if trace_count > 0:
        statuses = traces_df["status"].astype(str).str.upper()
        error_count = int(statuses.str.contains("ERROR|FAIL", regex=True).sum())
        error_rate = round(100.0 * error_count / trace_count, 2)
        if "execution_time_ms" in traces_df.columns:
            lat = traces_df["execution_time_ms"].dropna()
            if len(lat) > 0:
                avg_latency_ms = round(float(lat.mean()), 1)

    runs_df = mlflow.search_runs(
        experiment_ids=[experiment_id],
        max_results=1,
        order_by=["start_time DESC"],
    )
    quality_score = None
    latest_run_id = None
    latest_metrics = {}
    if runs_df is not None and not runs_df.empty:
        latest = runs_df.iloc[0]
        latest_run_id = latest.get("run_id")
        latest_metrics = {
            k.replace("metrics.", ""): v
            for k, v in latest.items()
            if str(k).startswith("metrics.") and v == v
        }
        quality_score = _extract_quality_score(latest_metrics)

    status = _classify_health(trace_count, error_rate, quality_score)
    return {
        "experiment_id": experiment_id,
        "name": name,
        "status": status,
        "trace_count": trace_count,
        "error_rate_pct": error_rate,
        "avg_latency_ms": avg_latency_ms,
        "quality_score": round(quality_score, 3) if quality_score is not None else None,
        "latest_run_id": latest_run_id,
        "latest_metrics": latest_metrics,
    }


@mcp.tool()
@with_timeout(SUMMARY_TIMEOUT)
@with_retry()
def summarize_experiment_health(
    experiment_ids: str = "",
    max_traces: int = 100,
) -> str:
    """Summarize fleet health for quality dashboards (error rate, latency, quality).

    Aggregates traces and latest evaluation runs server-side so clients do not need
    direct MLflow SDK access. Use this for Observatory / quality-dashboard views.

    Args:
        experiment_ids: Comma-separated experiment IDs. Empty = all experiments (capped).
        max_traces: Max traces to sample per experiment for error/latency stats.
    """
    try:
        client = _get_client()
        experiments = []

        if experiment_ids.strip():
            for eid in [x.strip() for x in experiment_ids.split(",") if x.strip()]:
                try:
                    exp = client.get_experiment(eid)
                    experiments.append((exp.experiment_id, exp.name))
                except Exception:
                    experiments.append((eid, eid))
        else:
            found = client.search_experiments(max_results=MAX_SUMMARY_EXPERIMENTS)
            experiments = [(e.experiment_id, e.name) for e in found]

        agents = []
        for eid, name in experiments:
            try:
                agents.append(_summarize_one_experiment(eid, name, max_traces))
            except Exception as e:
                agents.append({
                    "experiment_id": eid,
                    "name": name,
                    "status": "CRITICAL",
                    "trace_count": 0,
                    "error_rate_pct": None,
                    "avg_latency_ms": None,
                    "quality_score": None,
                    "latest_run_id": None,
                    "latest_metrics": {},
                    "error": str(e),
                })

        fleet = {"HEALTHY": 0, "WARNING": 0, "CRITICAL": 0, "INACTIVE": 0}
        for a in agents:
            fleet[a["status"]] = fleet.get(a["status"], 0) + 1

        alerts = []
        for a in agents:
            if a["status"] in ("CRITICAL", "WARNING", "INACTIVE"):
                if a["status"] == "INACTIVE":
                    issue = "No traces recorded"
                elif a.get("error"):
                    issue = a["error"]
                elif a["status"] == "CRITICAL":
                    issue = (
                        f"Error rate {a['error_rate_pct']}% or quality "
                        f"{a['quality_score']} below critical thresholds"
                    )
                else:
                    issue = (
                        f"Error rate {a['error_rate_pct']}% or quality "
                        f"{a['quality_score']} needs attention"
                    )
                alerts.append({
                    "severity": a["status"],
                    "agent": a["name"],
                    "experiment_id": a["experiment_id"],
                    "issue": issue,
                })

        return json.dumps({
            "generated_at": datetime.utcnow().isoformat(),
            "fleet_summary": fleet,
            "agents": agents,
            "alerts": alerts,
            "experiments_scanned": len(agents),
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e), "fleet_summary": {}, "agents": [], "alerts": []})


# =============================================================================
# SMART SAMPLING (review queue)
# =============================================================================


@mcp.tool()
@with_timeout(DEFAULT_TIMEOUT)
@with_retry()
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
@with_timeout(DEFAULT_TIMEOUT)
def health_check() -> str:
    """Check connectivity to MLflow and return system status."""
    try:
        uri = mlflow.get_tracking_uri()
        client = _get_client()
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

    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route, Mount

    async def health_check(request):
        return JSONResponse({"status": "ok", "service": "agent-lens-mcp", "version": "2.0"})

    mcp_app = mcp.streamable_http_app()
    app = Starlette(
        routes=[
            Route("/health", health_check),
            Mount("/mcp", app=mcp_app),
        ],
    )

    uvicorn.run(app, host=host, port=port)
