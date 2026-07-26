---
sidebar_position: 2
title: Getting Started
---

# Getting Started

## Prerequisites

- Python 3.11+
- MLflow Tracking Server (local or remote)
- An OpenAI-compatible LLM API key (Gemini, OpenAI, Azure, Ollama, etc.)
- For production: Kubernetes cluster with OpenShell Sandbox

**Two separate services need API keys:**

| Service | What it needs | Why |
|---------|---------------|-----|
| **Agent Lens (agent harness)** | Any OpenAI-compatible API key | Powers the conversational agent that talks to you |
| **MLflow MCP Server** | `OPENAI_API_KEY` + `MLFLOW_TRACKING_INSECURE_TLS` | Required for LLM-judge scorers (`evaluate_traces`, `register_llm_judge_scorer`) and TLS connectivity to MLflow |

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

### Step 1: Create the Agent Lens auth secret

```bash
DASH_PW=YourPassword API_KEY=YourKey LLM_API_KEY=YourGeminiOrOpenAIKey make secret-openshell
```

The `LLM_API_KEY` is mounted as `OPENAI_API_KEY` inside the Agent Lens pod. Any OpenAI-compatible key works (Gemini, OpenAI, Azure, Ollama).

### Step 2: Configure the MLflow MCP Server

The MLflow MCP server is a **separate deployment** from Agent Lens. It needs its own configuration:

```bash
# Required: Allow MCP server to connect to MLflow over self-signed TLS
oc set env deployment/mlflow-mcp MLFLOW_TRACKING_INSECURE_TLS=true -n <mlflow-namespace>

# Required for LLM-judge skills (evaluate-agent, create-judge, red-team, eval-loop):
oc set env deployment/mlflow-mcp OPENAI_API_KEY=<your-openai-key> -n <mlflow-namespace>
```

:::danger Critical: MLFLOW_TRACKING_INSECURE_TLS
If your MLflow Tracking Server uses self-signed TLS certificates (standard on OpenShift), you **must** set `MLFLOW_TRACKING_INSECURE_TLS=true` on the MLflow MCP deployment. Without this, **all MCP tool calls will hang silently** — no error, no timeout message, just infinite waiting. This was the #1 deployment issue found during testing.
:::

:::warning LLM Judge Model Compatibility
MLflow's built-in scorers (used by `evaluate_traces`) default to OpenAI model names like `gpt-4o-mini`. If you set `OPENAI_BASE_URL` to a Gemini endpoint, the scorer will fail because the model name doesn't exist on Gemini's API. For LLM-judge skills, use either:
- A real OpenAI API key (recommended), or
- An OpenAI-compatible proxy that translates model names
:::

### Step 3: Build and deploy Agent Lens

```bash
# Build the container image and deploy
make deploy-all

# Check status
make status
```

### Step 4: Access the dashboard

```bash
# Get the route URL
oc get route agent-lens -n openshell -o jsonpath='https://{.spec.host}'
```

Login with username `admin` and the dashboard password you set in the secret.

### Step 5: Verify MCP connectivity

In the dashboard, try: **"Show me all experiments"**

If it responds with a list of MLflow experiments, everything is working. If it hangs or times out, check the [Troubleshooting](#troubleshooting) section below.

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

## Troubleshooting

### MCP tool calls hang (no response, no error)

**Symptom:** You ask "Show me all experiments" and nothing happens — the agent just spins forever.

**Cause:** The MLflow MCP server cannot connect to the MLflow Tracking Server because of TLS certificate verification failure.

**Fix:**
```bash
oc set env deployment/mlflow-mcp MLFLOW_TRACKING_INSECURE_TLS=true -n <mlflow-namespace>
```
Then restart the Agent Lens pod so it picks up the fresh MCP connection:
```bash
oc delete pod agent-lens -n openshell
```

### LLM-judge evaluations fail with "OPENAI_API_KEY not set"

**Symptom:** Skills that use `evaluate_traces` or `register_llm_judge_scorer` return errors like `OPENAI_API_KEY environment variable must be set to use the openai provider`.

**Cause:** The MLflow MCP server (not Agent Lens) needs an OpenAI API key to run LLM-based scorers. This is separate from the Hermes LLM key.

**Fix:**
```bash
oc set env deployment/mlflow-mcp OPENAI_API_KEY=<key> -n <mlflow-namespace>
```

### LLM-judge evaluations fail with ChatCompletionError

**Symptom:** `evaluate_traces` returns `ChatCompletionError` or `Failed to invoke judge model`.

**Cause:** MLflow's built-in scorers default to OpenAI model names (e.g., `gpt-4o-mini`). If you set `OPENAI_BASE_URL` to a non-OpenAI endpoint (like Gemini), the model name is invalid.

**Fix:** Use a real OpenAI API key, or set up an OpenAI-compatible proxy that handles model name translation.

**Affected skills:** evaluate-agent, create-judge, red-team, eval-loop. All other skills (12 out of 16) work with any LLM provider.

### Pod keeps getting evicted (ephemeral-storage)

**Symptom:** Agent Lens pod enters `Error` or `Evicted` state with `The node was low on resource: ephemeral-storage`.

**Cause:** The Kubernetes node has too many container images or orphaned pods consuming disk space.

**Fix:**
```bash
# Delete failed pods that are consuming metadata space
oc delete pods --field-selector=status.phase=Failed -n <namespace> --wait=false

# If the pod keeps landing on the same bad node (PVC-bound), delete the workspace PVC
# to let OpenShift schedule on a healthy node:
oc delete pod agent-lens -n openshell
oc delete pvc workspace-agent-lens -n openshell
# The sandbox controller will create a new PVC on a healthy node
```

### Dashboard returns 302 but won't load

**Symptom:** The route is accessible (302 redirect) but the dashboard doesn't load.

**Fix:** The dashboard is on port 9119. Verify the route targets this port:
```bash
oc get route agent-lens -n openshell -o jsonpath='{.spec.port.targetPort}'
```

### "Show me all experiments" works but other skills time out

**Symptom:** Simple MCP queries work but complex skills (executive-summary, compliance-export) time out in CLI mode.

**Cause:** Some skills require multiple sequential MCP calls. CLI mode has shorter timeouts than the dashboard.

**Fix:** Use the web dashboard instead of CLI mode for complex skills. The dashboard handles long-running MCP workflows better.

### Which skills work without an OpenAI key?

These 12 skills work with **any** LLM provider (Gemini, Ollama, etc.) because they only use MCP data tools, not LLM judges:

| Skill | What it does |
|-------|-------------|
| trace-explorer | List experiments and traces |
| quality-dashboard | Fleet health overview |
| analyze-session | Trace analysis |
| review-trace | Deep trace inspection |
| create-regression | Flag traces as regressions |
| compare-evaluations | Side-by-side run comparison |
| cost-quality | Quality vs cost analysis |
| audit-trail | Qualification decision history |
| agent-registry | Fleet inventory |
| executive-summary | Board-ready health summary |
| compliance-export | JSONL/CSV export |
| aggregate-traces | Error rates, latency trends |

These 4 skills **require an OpenAI-compatible API key on the MLflow MCP server** for LLM judges:

| Skill | What it does |
|-------|-------------|
| evaluate-agent | Run scorers against traces |
| create-judge | Register custom LLM judge scorers |
| red-team | Adversarial safety evaluation |
| eval-loop | Full EDD improvement cycle |
