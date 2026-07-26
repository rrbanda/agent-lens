---
name: "agent-registry"
description: "Fleet inventory of all agents with qualification status, configuration, and lifecycle metadata. Use when asked about agent inventory, fleet overview, registration, or which agents are qualified."
---

# Agent Registry

Centralized fleet inventory derived from MLflow experiments and evaluation runs.

## When to Use

- "Show me all registered agents"
- "What agents are qualified for production?"
- "What's the status of our agent fleet?"
- "Which agents need re-qualification?"

## Strategy

### Step 1: List agent experiments

`mcp_mlflow_search_experiments` — each experiment represents an agent. Read experiment names and metadata.

### Step 2: Enrich with qualification data

For each experiment:
1. `mcp_mlflow_list_runs` — find evaluation runs with qualification parameters
2. `mcp_mlflow_describe_run` — read metrics (pass_rate, error_rate) and tags (profile, verdict)
3. `mcp_mlflow_search_traces` — recent trace activity (success rate, volume)

Derive qualification status from evaluation run history:
- **QUALIFIED** — latest eval run has `pass_rate >= 0.80` and `error_rate < 0.05`
- **NOT QUALIFIED** — latest eval run failed thresholds
- **PENDING** — no evaluation runs exist
- **NEEDS REVIEW** — inconclusive or mixed results

### Step 3: Present fleet view

## Output Format

```
## Agent Registry
### Fleet: [N] agents | Qualified: [X] | Pending: [Y] | Not Qualified: [Z]

| Agent | Type | Status | Last Evaluated | Pass Rate | Error Rate |
|-------|------|--------|---------------|-----------|------------|
| customer-support-agent | RAG | QUALIFIED | 2026-07-15 | 92% | 2% |
| support-bot | Chat | NOT QUALIFIED | 2026-07-10 | 68% | 8% |
| data-analyst | Tool-Calling | PENDING | — | — | — |

### Agents Needing Attention
- **support-bot**: Failed qualification on 2026-07-10 (pass_rate 68%)
- **data-analyst**: Never evaluated — no evaluation runs
```

## Lifecycle States

| State | Meaning | Next action |
|-------|---------|-------------|
| PENDING | Experiment exists, never evaluated | Run `evaluate-agent` |
| QUALIFIED | Latest eval passed thresholds | Re-qualify periodically |
| NOT_QUALIFIED | Latest eval failed thresholds | Fix issues, re-evaluate |
| NEEDS_REVIEW | Inconclusive evaluation | Manual review required |

> **Note:** `search_logged_models` is not yet in the MLflow MCP tool set.
> Until then, fleet status is derived from experiments, evaluation runs, and trace data.

## Constraints

- All data sourced from MLflow MCP — no separate database
- Cap fleet scans at 50 experiments
- Never `import mlflow` in the sandbox
