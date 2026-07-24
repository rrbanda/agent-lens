# Agent Lens — Hermes evaluation agent

Conversational evaluation for platform teams via **upstream official MLflow MCP** only.

## Features (skills)

| Skill | Trigger | Official MCP tools |
|-------|---------|-------------------|
| `evaluate-agent` | Evaluate, Score, Certify | `evaluate_traces`, `list_scorers` (pass rates ≥80%) |
| `review-trace` | Review, Annotate | `get_trace`, `search_traces`, `log_trace_feedback`, `log_trace_expectation` |
| `analyze-session` | Chat session / multi-turn | `search_traces`, `get_trace` |
| `create-regression` | Regression follow-up | `log_trace_expectation`, `set_trace_tag` |
| `trace-explorer` | Show traces, Errors | `search_traces`, `get_trace` |
| `quality-dashboard` | Overview, Fleet health | `search_experiments`, `search_traces`, `list_runs` (max 20) |

See [../docs/limitations.md](../docs/limitations.md) and [../docs/enterprise-readiness.md](../docs/enterprise-readiness.md).

## Prerequisites

- Official MLflow MCP (`mlflow-mcp`) — [../docs/operator-mcp.md](../docs/operator-mcp.md)
- Gemini API key; OpenShift + RHOAI + MLflow

## Secrets

```bash
make secret   # agent-lens-llm-key + agent-lens-auth
```

## Deploy

```bash
make deploy-agent
# Production image (recommended):
make build-agent
oc set image deploy/agent-lens hermes=quay.io/rrbanda/agent-lens:v3 -n agent-lens
oc set env deploy/agent-lens BOOTSTRAP_DEPS=0 -n agent-lens
```

MCP URL: env `MLFLOW_MCP_URL` overrides ConfigMap at startup.
