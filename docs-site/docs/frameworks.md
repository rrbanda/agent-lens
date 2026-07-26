---
sidebar_position: 5
title: Supported Frameworks
---

# Supported Frameworks

Agent Lens evaluates **any agent that sends traces to MLflow**. The framework doesn't matter — only that MLflow receives traces.

## Two dimensions of framework independence

### 1. Agents being evaluated (target agents)

These are the agents whose quality you want to assess. They run independently from Agent Lens and send traces to MLflow.

| Framework | MLflow Integration | Autolog |
|-----------|-------------------|---------|
| **LangGraph** | `mlflow.langchain.autolog()` | One-line — traces flow automatically |
| **Google ADK** | `mlflow.tracing.enable()` or ADK's built-in tracing with MLflow export | Configure `MLFLOW_TRACKING_URI` on your ADK agent |
| **LangChain** | `mlflow.langchain.autolog()` | One-line — traces flow automatically |
| **CrewAI** | `mlflow.crewai.autolog()` | One-line — traces flow automatically |
| **OpenAI Agents SDK** | `mlflow.openai.autolog()` | One-line — traces flow automatically |
| **AutoGen** | `mlflow.autogen.autolog()` or `@mlflow.trace` decorator | Autolog or manual |
| **LlamaIndex** | `mlflow.llama_index.autolog()` | One-line — traces flow automatically |
| **Custom Python** | `@mlflow.trace` decorator or `usercustomize.py` drop-in | See below |
| **Any language** | MLflow REST API (`POST /api/2.0/mlflow/traces`) | HTTP — no SDK needed |

### 2. Agent Lens runtime (qualification harness)

This is the conversational agent that interprets your natural language requests and calls MLflow MCP tools. It ships with **Hermes** as the reference runtime, but the core artifacts are portable.

| Artifact | Portable? | Notes |
|----------|-----------|-------|
| `agent-lens/skills/*.md` | Yes | Plain markdown. Any MCP agent can interpret them. |
| `agent-lens/soul.md` | Yes | Agent identity and constraints. Standard prompt engineering. |
| `agent-lens/config.yaml` | Mostly | MCP URL and tool allowlist are universal. |
| `Containerfile` | No | Installs specific harness. Replace for your runtime. |
| `startup.sh` | No | Launches harness processes. Replace for your runtime. |

## Instrumentation examples

### LangGraph / LangChain

```python
import mlflow
mlflow.langchain.autolog()

# Your LangGraph agent code runs as usual
# Traces flow to MLflow automatically
```

### Google ADK

```python
import mlflow
mlflow.tracing.enable()

# Or configure ADK's built-in tracing to export to MLflow
# Set MLFLOW_TRACKING_URI in your ADK agent's environment
```

### CrewAI

```python
import mlflow
mlflow.crewai.autolog()

# Your CrewAI agent code runs as usual
# Traces flow to MLflow automatically
```

### OpenAI Agents SDK

```python
import mlflow
mlflow.openai.autolog()

# Your OpenAI agent code runs as usual
# Traces flow to MLflow automatically
```

### AutoGen

```python
import mlflow
mlflow.autogen.autolog()

# Or use the @mlflow.trace decorator on specific functions
```

### Zero-code (any Python agent)

```bash
cp instrumentation/usercustomize.py $(python -m site --user-site)/
export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
export MLFLOW_EXPERIMENT_NAME="my-agent"
# No code changes needed — traces flow automatically
```

### Non-Python agents (REST API)

Any agent in any language can send traces via the MLflow REST API:

```bash
curl -X POST https://your-mlflow:8443/api/2.0/mlflow/traces \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "1",
    "timestamp_ms": 1721900000000,
    "request": {"messages": [{"role": "user", "content": "Hello"}]},
    "response": {"choices": [{"message": {"content": "Hi there!"}}]}
  }'
```

## What happens after traces arrive

Once traces are in MLflow, Agent Lens can:

1. **Observe** — `search_experiments`, `search_traces`, `get_trace`
2. **Evaluate** — `evaluate_traces` with built-in or custom scorers
3. **Annotate** — `log_trace_feedback`, `set_trace_tag`
4. **Qualify** — PASS/FAIL verdicts against configurable thresholds
5. **Report** — Fleet dashboards, executive summaries, compliance exports

The framework that produced the traces is irrelevant. Agent Lens works with the traces, not the agent code.
