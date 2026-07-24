# First-trace activation

Agent Lens cannot evaluate or dashboard agents that have never written traces to
MLflow. Complete this guide **before** a demo.

## Scope

[`instrumentation/usercustomize.py`](../instrumentation/usercustomize.py) enables
`mlflow.openai.autolog` for **OpenAI-compatible Python** agents when:

- `mlflow` is installed in the agent environment
- `MLFLOW_TRACKING_URI` is set
- `MLFLOW_EXPERIMENT_NAME` (or experiment id) is set

It is silent if those are missing. Non-Python / non-OpenAI stacks need a different
instrumentation path (out of scope for this helper).

## Steps

1. Copy the helper into the target agent's environment:

```bash
cp instrumentation/usercustomize.py "$(python -m site --user-site)/usercustomize.py"
```

2. Set env on the agent Deployment / runtime:

```bash
export MLFLOW_TRACKING_URI="https://mlflow.<your-cluster>:8443"
export MLFLOW_EXPERIMENT_NAME="my-agent"
# Plus any token / CA vars your cluster requires
```

3. Exercise the agent (at least a few LLM calls).

4. Verify in the **MLflow UI** (or CLI) that the experiment has traces with status OK
   or ERROR. Do **not** open Agent Lens until you see traces.

5. In Agent Lens:

```text
What experiments are being tracked?
Show me the last 20 traces for my-agent
```

## Success criteria

- `search_experiments` lists your experiment
- `search_traces` returns ≥1 row
- Quality dashboard shows HEALTHY / WARNING / CRITICAL — not only INACTIVE

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No experiment | Wrong workspace / tracking URI / name |
| Experiment empty | Agent not calling OpenAI-compatible client; usercustomize not loaded |
| Agent Lens INACTIVE | Traces exist in another experiment id — pass the correct name/id |
