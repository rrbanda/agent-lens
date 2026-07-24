---
name: "quality-dashboard"
description: "Generate a full observability summary across all tracked agents: top experiments, recent runs, health scores, and alerts. Use when asked for an overview or 'how are things going' type questions."
---

# Quality Dashboard

Fleet-wide observability summary across all tracked agents via **upstream official MLflow MCP**.

## Strategy (MCP-first — required)

1. Call `mcp_mlflow_search_experiments` to list active experiments (agents).
2. Cap the fleet scan at **20 experiments** (prefer recently updated). Say so in the report if truncated.
3. For each selected experiment:
   - `mcp_mlflow_search_traces` with that experiment id (`max_results` 50)
   - Optionally `mcp_mlflow_list_runs` for recent evaluation metrics
4. Compute status with the criteria table (code execution may aggregate MCP JSON only).
5. Format the Observatory output below.

Do **not** open code execution to call MLflow. Only use it on data already returned by MCP.

## Anti-patterns (never do this)

> **Do not** `import mlflow`, call `mlflow.set_tracking_uri`, or connect to an MLflow
> database / tracking server from the Hermes code-execution sandbox. That environment
> has no ServiceAccount token to RHOAI MLflow and will hang or fail. All MLflow access
> must go through official MCP tools (`mcp_mlflow_*`).

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
