# MLflow MCP Server

A lightweight [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes MLflow experiment tracking data as callable tools for AI agents.

## Tools Exposed

| Tool | Description |
|------|-------------|
| `list_experiments` | List all MLflow experiments |
| `get_experiment` | Get experiment details by ID |
| `search_runs` | Search runs with filters |
| `get_run` | Get full run details |
| `get_metric_history` | Metric values over time |
| `compare_runs` | Side-by-side run comparison |
| `search_traces` | Search agent traces |
| `set_trace_tag` | Tag traces for tracking |
| `log_feedback` | Log evaluation scores on traces |
| `health_check` | Server connectivity check |

## Quick Start (Local)

```bash
export MLFLOW_TRACKING_URI="https://your-mlflow-server:8443"
export MLFLOW_WORKSPACE="default"

pip install -r requirements.txt
python entrypoint.py
```

Server starts on `http://0.0.0.0:8080/mcp` (streamable-http transport).

## Container Build

```bash
podman build -t mlflow-mcp-server:latest -f Containerfile .
```

## Kubernetes Deployment

```bash
# Customize the ConfigMap values for your cluster
cd deploy/
# Edit kustomization.yaml to set tracking-uri and default-workspace
oc apply -k .
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | `https://mlflow-server:8443` | MLflow server URL |
| `MLFLOW_WORKSPACE` | `default` | Default workspace (k8s namespace) |
| `MLFLOW_TRACKING_TOKEN_FILE` | SA token path | Bearer token for auth |
| `MLFLOW_TRACKING_INSECURE_TLS` | `true` | Skip TLS verification |
| `MCP_HOST` | `0.0.0.0` | Server bind address |
| `MCP_PORT` | `8080` | Server bind port |
