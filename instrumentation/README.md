# Agent Lens — Instrumentation

Tools to add observability to **target** AI agents (not Hermes). Hermes talks to
MLflow only via **official MCP** — never run these patterns inside the Agent Lens sandbox.

## Components

### 1. `usercustomize.py` — Zero-code auto-instrumentation

Drop into a target agent's Python environment. Enables `mlflow.openai.autolog` when
`MLFLOW_TRACKING_URI` and `MLFLOW_EXPERIMENT_NAME` are set.

```bash
cp usercustomize.py "$(python -m site --user-site)/usercustomize.py"
export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
export MLFLOW_EXPERIMENT_NAME="my-agent"
```

**Scope:** OpenAI-compatible Python clients. For LangChain / LangGraph / Anthropic /
LiteLLM, use the matching `mlflow.*.autolog` (see [mlflow/skills instrumenting-with-mlflow-tracing](https://github.com/mlflow/skills/tree/main/instrumenting-with-mlflow-tracing)).

**RAG note:** `RetrievalGroundedness` needs retrieval/`RETRIEVER` spans. Plain OpenAI
chat autolog may not create them.

See also [docs/first-trace.md](../docs/first-trace.md).

### 2. `eval_agent.py` — Offline CLI evaluation

Runs **outside** Hermes with tracking credentials. Uses `mlflow.genai.evaluate` and
built-in GenAI scorers (yes/no pass rates). Requires **MLflow 3.8+**.

```bash
export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
export AGENT_API_URL="http://agent-service:8642"
export AGENT_API_KEY="agent-api-key"

python eval_agent.py --experiment-name "my-agent" --profile chat
# profiles: rag | tool-calling | chat
```

Custom prompts JSON:

```json
[
  {"prompt": "Your question", "context": "Optional grounding context"}
]
```

## Metrics (GenAI)

| Scorer | Measures |
|--------|----------|
| RelevanceToQuery | Output addresses the request |
| RetrievalGroundedness | Grounded in retrieved context (needs retriever spans) |
| ToolCallCorrectness / Efficiency | Tool use quality |
| Guidelines | Custom policy bars |

Report **pass rates**, not 1–5 Likert scores.
