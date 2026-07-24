# Agent Lens — Instrumentation

Tools to add observability to **any** AI agent running on the platform.

## Components

### 1. `usercustomize.py` — Zero-Code Auto-Instrumentation

Drop into a target agent's Python environment. Every OpenAI-compatible LLM call
is automatically captured as an MLflow trace — no code changes required.

```bash
# Install into the agent's site-packages
cp usercustomize.py $(python -m site --user-site)/usercustomize.py

# Set required env vars on the agent
export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
export MLFLOW_EXPERIMENT_NAME="my-agent"
```

### 2. `eval_agent.py` — Evaluation Runner

Run systematic quality evaluations against any agent API and store results in MLflow.

```bash
export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
export AGENT_API_URL="http://agent-service:8642"
export AGENT_API_KEY="agent-api-key"

python eval_agent.py --experiment-name "my-agent" --workspace "my-namespace"
```

Custom prompts:

```bash
python eval_agent.py --experiment-name "my-agent" --prompts-file prompts.json
```

Format for `prompts.json`:
```json
[
  {"prompt": "Your question", "context": "Expected grounding context"},
  {"prompt": "Another question", "context": "More context"}
]
```

### 3. Kubernetes Sidecar (Optional)

For agents that don't use Python, inject a sidecar container that proxies LLM calls
and logs traces. See `deploy/` for manifests.

## Evaluation Metrics

| Metric | What It Measures |
|--------|-----------------|
| Relevance | Does the output address the user's request? |
| Faithfulness | Is the output grounded in provided context? |
| Correctness | Is the output factually accurate? |
| Token Count | Efficiency of the response |
| Latency | Response time |
