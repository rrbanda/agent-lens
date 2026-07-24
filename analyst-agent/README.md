# Agent Lens — Observability Agent

A [Hermes Agent](https://github.com/hermes-ai/hermes-agent) instance specialized in
AI agent observability. It connects to MLflow via MCP and provides conversational
access to experiments, traces, metrics, and evaluation scores.

## What It Does

Ask natural-language questions like:
- "How is the outreach agent performing today?"
- "Show me the last 10 traces with errors"
- "Compare the last two evaluation runs"
- "Generate a quality dashboard"

Agent Lens uses a **hybrid architecture**:
- **Native MCP tools** for simple lookups (list experiments, get a run)
- **Code execution** for complex multi-step analysis (error rate computation, trend analysis)

## Skills

| Skill | Trigger |
|-------|---------|
| `trace-explorer` | "Show traces", "Recent activity", "Error rate" |
| `eval-report` | "Quality scores", "Evaluation results" |
| `compare-agents` | "Compare runs", "Before/after" |
| `diagnose-failure` | "What went wrong", "Debug this trace" |
| `quality-dashboard` | "Overview", "How are things going" |

## Prerequisites

- MLflow MCP Server deployed and accessible (see `../mcp-server/`)
- Gemini API key (or any LLM provider supported by Hermes)
- OpenShift cluster with RHOAI and MLflow operator

## Deploy

```bash
# Create the secret first
oc create secret generic agent-lens-llm-key \
  --from-literal=api-key='YOUR_API_KEY' \
  -n agent-lens

# Deploy via kustomize
oc apply -k deploy/
```

## Configuration

Edit `config.yaml` to change:
- LLM provider (`model.provider` and `model.default`)
- MCP server URL (`mcp_servers.mlflow.url`)
- Dashboard credentials
- Enabled toolsets

## Local Development

```bash
export GEMINI_API_KEY="your-key"
pip install hermes-agent aiohttp mcp
hermes dashboard --no-open
```
