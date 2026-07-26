---
sidebar_position: 2
title: Getting Started
---

# Getting Started

## Prerequisites

- Python 3.11+
- MLflow Tracking Server (local or remote)
- For production: Kubernetes cluster with OpenShell

## Local Development

```bash
# Clone and setup
git clone https://github.com/rrbanda/agent-lens.git
cd agent-lens
make dev-setup

# Start MLflow and seed test data
make mlflow-start
make seed-data

# Run integration tests to verify everything works
make test-integration
```

## Deploy to OpenShift

```bash
# Create auth secret (dashboard password + LLM API key)
DASH_PW=YourPassword API_KEY=YourKey LLM_API_KEY=YourGeminiOrOpenAIKey make secret-openshell

# Build and deploy
make deploy-all

# Check status
make status
```

:::important MLflow MCP Server Configuration
The MLflow MCP server needs `MLFLOW_TRACKING_INSECURE_TLS=true` if your MLflow Tracking Server uses self-signed TLS certificates (common on OpenShift). Without this, MCP tool calls will hang silently.

For LLM-judge scorers (`evaluate_traces`, `register_llm_judge_scorer`), the MLflow MCP server also needs `OPENAI_API_KEY` and `OPENAI_BASE_URL` configured. MLflow's built-in scorers default to OpenAI model names — use a real OpenAI API key or configure a compatible endpoint.
:::

## Your First Interaction

Once deployed, open the dashboard route and try:

```
"List all MLflow experiments"
"Show me the last 10 traces for my-agent"
"Evaluate my-agent using the RAG profile"
"Give me a quality dashboard across all agents"
```

## How It Works

Agent Lens follows a five-phase loop:

| Phase | What Happens | MCP Tools Used |
|-------|-------------|----------------|
| **Observe** | Discover experiments, traces | `search_experiments`, `search_traces`, `get_trace` |
| **Evaluate** | Score traces with GenAI judges | `evaluate_traces`, `list_scorers` |
| **Annotate** | Log feedback / expectations | `log_trace_feedback`, `log_trace_expectation` |
| **Qualify** | PASS/FAIL against thresholds | Evaluation run metrics + trace tags |
| **Follow up** | Tag failures for regression | `set_trace_tag`, `log_trace_expectation` |

## MCP Tools Used

All tool calls go through the official MLflow MCP server (`mlflow mcp run`):

| Tool | Purpose |
|------|---------|
| `search_experiments` | Discover agent experiments |
| `get_experiment` | Get experiment details |
| `search_traces` | Find traces with filters |
| `get_trace` | Full trace with spans |
| `log_trace_feedback` | Human quality assessments |
| `log_trace_expectation` | Expected outputs for regression |
| `set_trace_tag` | Tag traces (regression, reviewed) |
| `evaluate_traces` | Run LLM judges on traces |
| `list_runs` | Find evaluation runs |
| `describe_run` | Get run metrics and tags |
| `list_scorers` | Available built-in judges (pass `builtin: "true"`) |
| `register_llm_judge_scorer` | Create custom LLM judge scorers |
| `create_run` | Record evaluation runs |
| `create_experiment` | Create new experiments |
| `delete_trace_tag` | Remove trace tags |
| `get_trace_assessment` | Read trace assessments |
| `update_trace_assessment` | Update trace assessments |
| `delete_trace_assessment` | Remove assessments |
| `link_traces_to_run` | Associate traces with runs |
| `delete_traces` | Remove traces |
