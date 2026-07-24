---
name: "quality-dashboard"
description: "Generate a full observability summary across all tracked agents: top experiments, recent runs, health scores, and alerts. Use when asked for an overview or 'how are things going' type questions."
---

# Quality Dashboard

Fleet-wide observability summary across all tracked agents.

## Strategy (MCP-first — required)

### Primary path (preferred)

1. Call `mcp_agent-lens_summarize_experiment_health` once.
   - Omit `experiment_ids` for the full fleet (server caps the scan).
   - Or pass a comma-separated list (e.g. `"28"`) for a single agent.
2. Format the JSON into the Observatory output below.
3. Do **not** open a code-execution session for this skill unless the primary tool fails.

### Fallback (only if summarize tool errors)

1. `mcp_agent-lens_list_experiments`
2. For each experiment: `mcp_agent-lens_search_traces` + `mcp_agent-lens_search_runs`
3. Compute status with the criteria table, then format Observatory output

## Anti-patterns (never do this)

> **Do not** `import mlflow`, call `mlflow.set_tracking_uri`, or connect to an MLflow
> database / tracking server from the Hermes code-execution sandbox. That environment
> has no ServiceAccount token to RHOAI MLflow and will hang or fail with configuration
> errors. All MLflow access must go through Agent Lens MCP tools.

If you use code execution at all (rare), call MCP over HTTP using `MLFLOW_MCP_URL`
(or the registered MCP client) — never the MLflow tracking SDK.

## Health Status Criteria

| Status | Conditions |
|--------|-----------|
| HEALTHY | Error rate < 5%, quality > 4.0, has traces |
| WARNING | Error rate 5-15%, quality 3.0-4.0, active but no eval scores, or reduced quality |
| CRITICAL | Error rate > 15%, quality < 3.0, or tool error fetching data |
| INACTIVE | No traces recorded in the experiment |

## Output Format

```
## AI Agent Observatory
Generated: [timestamp]

### Fleet Summary
| Status | Count |
|--------|-------|
| Healthy | N |
| Warning | N |
| Critical | N |
| Inactive | N |

---

### [Agent Name] (Experiment [id]) — [STATUS]
| Metric | Value | Trend |
|--------|-------|-------|
| Traces (sample) | N | up/down/stable |
| Error Rate | X% | up/down/stable |
| Avg Latency | Xms | up/down/stable |
| Quality Score | X.X/5.0 | up/down/stable |

---

### Alerts
| Severity | Agent | Issue |
|----------|-------|-------|
| CRITICAL | ... | ... |
| WARNING | ... | ... |

### Recommended Actions
1. [Most urgent — backed by data]
2. [Second priority]
3. [Optimization opportunity]
```

When status is INACTIVE, recommend instrumentation (`usercustomize.py` / MLflow autolog)
and optionally running `evaluate-agent` after traces exist — do not claim a configuration
error if MCP tools succeeded with empty traces.
