"""
Agent Lens — MLflow MCP Server

A lightweight Model Context Protocol (MCP) server that exposes MLflow
experiment tracking data (experiments, runs, traces, metrics) as
callable tools for AI agents.

Uses httpx for HTTP calls to MLflow REST API and FastMCP for the
MCP transport layer. No heavy mlflow package required at runtime.

Environment Variables:
    MLFLOW_TRACKING_URI: MLflow tracking server URL
    MLFLOW_WORKSPACE: Kubernetes namespace / MLflow workspace
    MLFLOW_TRACKING_TOKEN_FILE: Path to ServiceAccount token
    MLFLOW_TRACKING_INSECURE_TLS: Skip TLS verification (default: true)
    MCP_HOST: Bind host (default: 0.0.0.0)
    MCP_PORT: Bind port (default: 8080)
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional

import httpx
from fastmcp import FastMCP

mcp = FastMCP(
    name="mlflow-mcp",
    instructions=(
        "MLflow experiment tracking server. Use these tools to search experiments, "
        "runs, traces, log feedback, and manage ML metadata."
    ),
)


def _get_headers(workspace: str = "") -> dict:
    """Build auth headers using the mounted ServiceAccount token."""
    token_file = os.environ.get(
        "MLFLOW_TRACKING_TOKEN_FILE",
        "/var/run/secrets/kubernetes.io/serviceaccount/token",
    )
    headers = {"Content-Type": "application/json"}
    if os.path.isfile(token_file):
        with open(token_file) as f:
            headers["Authorization"] = f"Bearer {f.read().strip()}"
    elif os.environ.get("MLFLOW_TRACKING_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['MLFLOW_TRACKING_TOKEN']}"

    ws = workspace or os.environ.get("MLFLOW_WORKSPACE", "default")
    headers["X-MLflow-Workspace"] = ws
    return headers


def _base_url() -> str:
    return os.environ.get("MLFLOW_TRACKING_URI", "https://mlflow-server:8443")


def _api(method: str, path: str, body: Optional[dict] = None, workspace: str = "") -> dict:
    """Call the MLflow REST API."""
    url = f"{_base_url()}/api/2.0/mlflow{path}"
    verify = os.environ.get("MLFLOW_TRACKING_INSECURE_TLS", "true").lower() != "true"
    headers = _get_headers(workspace)
    try:
        if method == "GET":
            resp = httpx.get(url, headers=headers, verify=verify, timeout=30)
        else:
            resp = httpx.post(url, json=body or {}, headers=headers, verify=verify, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:300]}"}
    except Exception as e:
        return {"error": str(e)}


# --- Experiment Tools ---


@mcp.tool()
def list_experiments(workspace: str = "", max_results: int = 100) -> str:
    """List all MLflow experiments with their IDs, names, and lifecycle stage.

    Args:
        workspace: Kubernetes namespace (MLflow workspace). Defaults to env MLFLOW_WORKSPACE.
        max_results: Maximum experiments to return.
    """
    result = _api("GET", f"/experiments/search?max_results={max_results}", workspace=workspace)
    if "error" in result:
        return json.dumps(result, indent=2)
    experiments = result.get("experiments", [])
    return json.dumps([{
        "experiment_id": e.get("experiment_id"),
        "name": e.get("name"),
        "lifecycle_stage": e.get("lifecycle_stage"),
        "artifact_location": e.get("artifact_location"),
    } for e in experiments], indent=2)


@mcp.tool()
def get_experiment(experiment_id: str) -> str:
    """Get details of a specific experiment by ID."""
    result = _api("GET", f"/experiments/get?experiment_id={experiment_id}")
    if "error" in result:
        return json.dumps(result, indent=2)
    return json.dumps(result.get("experiment", result), indent=2)


# --- Run Tools ---


@mcp.tool()
def search_runs(
    experiment_id: str,
    filter_string: str = "",
    max_results: int = 25,
    order_by: str = "start_time DESC",
    workspace: str = "",
) -> str:
    """Search runs in an experiment with optional filtering and ordering.

    Args:
        experiment_id: The experiment ID to search in.
        filter_string: MLflow filter string, e.g. "metrics.accuracy > 0.9"
        max_results: Maximum number of runs to return.
        order_by: Order by clause, e.g. "metrics.accuracy DESC"
        workspace: Kubernetes namespace (MLflow workspace).
    """
    body = {
        "experiment_ids": [experiment_id],
        "max_results": max_results,
    }
    if filter_string:
        body["filter"] = filter_string
    if order_by:
        body["order_by"] = [order_by]

    result = _api("POST", "/runs/search", body)
    if "error" in result:
        return json.dumps(result, indent=2)
    runs = result.get("runs", [])
    return json.dumps([{
        "run_id": r.get("info", {}).get("run_id"),
        "run_name": r.get("info", {}).get("run_name"),
        "status": r.get("info", {}).get("status"),
        "start_time": r.get("info", {}).get("start_time"),
        "end_time": r.get("info", {}).get("end_time"),
        "metrics": {m["key"]: m["value"] for m in r.get("data", {}).get("metrics", [])},
        "params": {p["key"]: p["value"] for p in r.get("data", {}).get("params", [])},
    } for r in runs], indent=2)


@mcp.tool()
def get_run(run_id: str) -> str:
    """Get full details of a specific run including metrics, params, and tags."""
    result = _api("GET", f"/runs/get?run_id={run_id}")
    if "error" in result:
        return json.dumps(result, indent=2)
    run = result.get("run", result)
    info = run.get("info", {})
    data = run.get("data", {})
    return json.dumps({
        "run_id": info.get("run_id"),
        "run_name": info.get("run_name"),
        "experiment_id": info.get("experiment_id"),
        "status": info.get("status"),
        "start_time": info.get("start_time"),
        "end_time": info.get("end_time"),
        "artifact_uri": info.get("artifact_uri"),
        "metrics": {m["key"]: m["value"] for m in data.get("metrics", [])},
        "params": {p["key"]: p["value"] for p in data.get("params", [])},
        "tags": {t["key"]: t["value"] for t in data.get("tags", [])},
    }, indent=2)


@mcp.tool()
def get_metric_history(run_id: str, metric_key: str) -> str:
    """Get the full history of a metric for a specific run.

    Args:
        run_id: The run ID.
        metric_key: The metric name, e.g. "loss" or "accuracy".
    """
    result = _api("GET", f"/metrics/get-history?run_id={run_id}&metric_key={metric_key}")
    if "error" in result:
        return json.dumps(result, indent=2)
    metrics = result.get("metrics", [])
    return json.dumps([{
        "step": m.get("step"), "value": m.get("value"), "timestamp": m.get("timestamp")
    } for m in metrics], indent=2)


@mcp.tool()
def compare_runs(run_ids: str, metric_keys: str = "") -> str:
    """Compare multiple runs side by side.

    Args:
        run_ids: Comma-separated run IDs to compare.
        metric_keys: Comma-separated metric names to include (empty = all).
    """
    ids = [r.strip() for r in run_ids.split(",")]
    keys = [k.strip() for k in metric_keys.split(",") if k.strip()] if metric_keys else None
    results = []
    for run_id in ids:
        data = json.loads(get_run(run_id))
        if "error" in data:
            results.append({"run_id": run_id, "error": data["error"]})
            continue
        metrics = data.get("metrics", {})
        if keys:
            metrics = {k: v for k, v in metrics.items() if k in keys}
        results.append({
            "run_id": run_id,
            "run_name": data.get("run_name"),
            "status": data.get("status"),
            "metrics": metrics,
            "params": data.get("params", {}),
        })
    return json.dumps(results, indent=2)


# --- Trace Tools ---


@mcp.tool()
def search_traces(
    experiment_id: str,
    filter_string: str = "",
    max_results: int = 25,
) -> str:
    """Search traces in an experiment.

    Args:
        experiment_id: The experiment ID to search traces in.
        filter_string: Filter string for traces.
        max_results: Maximum number of traces to return.
    """
    params = f"/traces?experiment_ids={experiment_id}&max_results={max_results}"
    if filter_string:
        params += f"&filter={filter_string}"

    result = _api("GET", params)
    if "error" in result:
        return json.dumps(result, indent=2)
    traces = result.get("traces", [])
    return json.dumps([{
        "request_id": t.get("request_id"),
        "experiment_id": t.get("experiment_id"),
        "timestamp_ms": t.get("timestamp_ms"),
        "execution_time_ms": t.get("execution_time_ms"),
        "status": t.get("status"),
        "token_usage": t.get("request_metadata", [{}]),
    } for t in traces], indent=2)


@mcp.tool()
def set_trace_tag(trace_id: str, key: str, value: str) -> str:
    """Add or update a tag on a trace.

    Args:
        trace_id: The trace/request ID.
        key: Tag key.
        value: Tag value.
    """
    result = _api("POST", "/traces/set-tag", {
        "request_id": trace_id, "key": key, "value": value
    })
    if "error" in result:
        return json.dumps(result, indent=2)
    return json.dumps({"status": "ok", "trace_id": trace_id, "tag": {key: value}})


# --- Feedback / Assessment Tools ---


@mcp.tool()
def log_feedback(trace_id: str, name: str, value: float, rationale: str = "") -> str:
    """Log an evaluation score or judgment for a trace.

    Args:
        trace_id: The trace/request ID.
        name: Assessment name (e.g. "relevance", "accuracy").
        value: Numeric score.
        rationale: Optional explanation for the score.
    """
    result = _api("POST", "/traces/set-tag", {
        "request_id": trace_id,
        "key": f"assessment.{name}.value",
        "value": str(value),
    })
    if "error" in result:
        return json.dumps(result, indent=2)
    if rationale:
        _api("POST", "/traces/set-tag", {
            "request_id": trace_id,
            "key": f"assessment.{name}.rationale",
            "value": rationale,
        })
    return json.dumps({
        "status": "ok", "trace_id": trace_id,
        "assessment": {"name": name, "value": value, "rationale": rationale},
    })


# --- Health Check ---


@mcp.tool()
def health_check() -> str:
    """Check connectivity to the MLflow tracking server and return status."""
    base = _base_url()
    verify = os.environ.get("MLFLOW_TRACKING_INSECURE_TLS", "true").lower() != "true"
    headers = _get_headers()
    try:
        resp = httpx.get(
            f"{base}/api/2.0/mlflow/experiments/search?max_results=1",
            headers=headers, verify=verify, timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            count = len(data.get("experiments", []))
            return json.dumps({
                "status": "healthy",
                "tracking_uri": base,
                "workspace": headers.get("X-MLflow-Workspace"),
                "experiments_found": count,
                "timestamp": datetime.utcnow().isoformat(),
            }, indent=2)
        else:
            return json.dumps({
                "status": "degraded",
                "tracking_uri": base,
                "http_status": resp.status_code,
                "response": resp.text[:300],
            }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "unhealthy",
            "tracking_uri": base,
            "error": str(e),
        }, indent=2)


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))

    print(f"Starting MLflow MCP server on {host}:{port}", file=sys.stderr)
    print(f"  MLFLOW_TRACKING_URI = {os.environ.get('MLFLOW_TRACKING_URI', 'not set')}", file=sys.stderr)
    print(f"  MLFLOW_WORKSPACE = {os.environ.get('MLFLOW_WORKSPACE', 'default')}", file=sys.stderr)
    print(f"  Transport = streamable-http at /mcp", file=sys.stderr)

    mcp.run(transport="streamable-http", host=host, port=port)
