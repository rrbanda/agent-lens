# Agent Lens — Evaluation Agent

A [Hermes Agent](https://github.com/hermes-ai/hermes-agent) instance specialized in
AI agent evaluation for platform teams. It connects to MLflow via the **upstream
official MLflow MCP** (`mlflow mcp run`) only.

## What it does

Ask natural-language questions like:

- "Evaluate the outreach agent using the tool-calling profile"
- "Show me traces that need review"
- "Annotate that trace as incorrect — tool selection was wrong"
- "Log a regression follow-up for this failure"
- "Can this agent be certified for deploy?" (chat verdict — not a CI block)
- "Give me a quality dashboard across all agents"

**MCP-first:**

- All MLflow access via `mcp_mlflow_*` tools
- Code execution only formats MCP JSON — never `import mlflow` in the sandbox

See [../docs/limitations.md](../docs/limitations.md) for gate / dataset / queue honesty.

## Skills

| Skill | Trigger | Official MCP tools |
|-------|---------|-------------------|
| `evaluate-agent` | Evaluate, Score, Certify | `evaluate_traces`, `list_scorers` |
| `review-trace` | Review, Annotate | `get_trace`, `search_traces`, `log_trace_feedback`, `log_trace_expectation` |
| `create-regression` | Regression follow-up | `log_trace_expectation`, `set_trace_tag` |
| `trace-explorer` | Show traces, Errors | `search_traces`, `get_trace` |
| `quality-dashboard` | Overview, Fleet health | `search_experiments`, `search_traces`, `list_runs` (max 20 experiments) |

## Prerequisites

- Official MLflow MCP (`mlflow-mcp`) — [../docs/operator-mcp.md](../docs/operator-mcp.md)
- Gemini API key
- OpenShift + RHOAI + MLflow

## Secrets

| Secret | Keys |
|--------|------|
| `agent-lens-llm-key` | `api-key` |
| `agent-lens-auth` | `dashboard-password`, `api-server-key` |

```bash
make secret   # from repo root — creates both
```

## MCP URL (single source at runtime)

1. Set `MLFLOW_MCP_URL` on the Deployment (default official in-cluster URL)
2. Startup script writes that URL into Hermes `config.yaml` `mcp_servers.mlflow.url`
3. Keep [`config.yaml`](config.yaml) allowlist in sync with upstream tool names

## Deploy

```bash
oc apply -k deploy/
# or from repo root:
make deploy-agent
```

## Local development

```bash
export GEMINI_API_KEY="your-key"
export MLFLOW_MCP_URL="http://localhost:8080/mcp"  # port-forward official MCP
pip install hermes-agent aiohttp mcp pyyaml
# Point config.yaml url at MLFLOW_MCP_URL before starting
hermes dashboard --no-open
```
