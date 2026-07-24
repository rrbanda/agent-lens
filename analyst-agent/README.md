# Agent Lens — Evaluation Agent

A [Hermes Agent](https://github.com/hermes-ai/hermes-agent) instance specialized in
AI agent evaluation and governance. It connects to MLflow via MCP and provides
conversational access to evaluation scoring, trace annotation, quality gates, and
regression dataset management.

## What It Does

Ask natural-language questions like:
- "Evaluate the outreach agent using the tool-calling profile"
- "Show me traces that need review"
- "Annotate that trace as incorrect — tool selection was wrong"
- "Add the failing trace to the regression dataset"
- "Can this agent be deployed? Check the quality gate"
- "Give me a quality dashboard across all agents"

Agent Lens uses a **hybrid architecture**:
- **Native MCP tools** for evaluation actions (run scorers, annotate, gate, fleet health)
- **Code execution** only on data already returned via MCP — never `import mlflow` in the sandbox

## Skills

| Skill | Trigger | MCP Tools Used |
|-------|---------|---------------|
| `evaluate-agent` | "Evaluate", "Score", "Certify" | `run_evaluation`, `list_scorers` |
| `review-trace` | "Review", "Annotate", "Feedback" | `get_review_queue`, `annotate_trace`, `set_expectation` |
| `create-regression` | "Add to dataset", "Regression test" | `create_test_case`, `list_datasets` |
| `trace-explorer` | "Show traces", "Recent activity", "Errors" | `search_traces`, `get_trace` |
| `quality-dashboard` | "Overview", "Fleet health", "Dashboard" | `summarize_experiment_health` |

## Prerequisites

- MLflow MCP Server deployed and accessible (see `../mcp-server/`)
- Gemini API key (or any LLM provider supported by Hermes)
- OpenShift cluster with RHOAI and MLflow operator

## Deploy

```bash
# Create secrets
oc create secret generic agent-lens-llm-key \
  --from-literal=api-key='YOUR_GEMINI_API_KEY' \
  -n agent-lens

oc create secret generic agent-lens-auth \
  --from-literal=api-server-key='YOUR_API_KEY' \
  --from-literal=dashboard-password='YOUR_PASSWORD' \
  -n agent-lens

# Deploy via kustomize
oc apply -k deploy/
```

## Configuration

Edit `config.yaml` to change:
- LLM provider (`model.provider` and `model.default`)
- MCP server URL (`mcp_servers.mlflow.url`)
- Enabled toolsets

## Local Development

```bash
export GEMINI_API_KEY="your-key"
pip install hermes-agent aiohttp mcp
hermes dashboard --no-open
```
