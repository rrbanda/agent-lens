---
name: "quality-dashboard"
description: "Generate a full observability summary across all tracked agents: top experiments, recent runs, health scores, and alerts. Use when asked for an overview or 'how are things going' type questions."
---

# Quality Dashboard

Fleet-wide observability summary across all tracked agents.

## Strategy

1. System health — call `mcp_mlflow_list_experiments` to enumerate tracked agents
2. For each active experiment:
   - Call `mcp_mlflow_search_traces` (recent activity, error rate)
   - Call `mcp_mlflow_search_runs` (latest eval scores)
3. Compute health status per agent
4. Surface alerts for anything outside normal bounds

## Health Status Criteria

| Status | Conditions |
|--------|-----------|
| HEALTHY | Error rate < 5%, quality > 4.0, active in last 24h |
| WARNING | Error rate 5-15%, quality 3.0-4.0, or reduced activity |
| CRITICAL | Error rate > 15%, quality < 3.0, or no traces in 24h |
| INACTIVE | No traces recorded in the experiment |

## When to Use Code Execution

This skill almost always benefits from code execution because it aggregates
data across multiple experiments and computes derived metrics (error rates,
averages). Use native tools only if there's a single experiment to check.

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
| Traces (24h) | N | up/down/stable |
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
