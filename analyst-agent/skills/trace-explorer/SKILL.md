---
name: "trace-explorer"
description: "Search and summarize traces from any agent's MLflow experiment. Shows latency, token usage, error rates, and interaction patterns. Use when asked about recent agent activity or trace details."
---

# Trace Explorer

Investigate agent activity by querying trace data from MLflow.

## Strategy

1. Identify the target experiment — call `mcp_agent-lens_list_experiments` if unknown
2. Search traces — call `mcp_agent-lens_search_traces` with the experiment_id
3. Analyze for patterns:
   - **Error rate**: count ERROR status vs total
   - **Latency distribution**: identify p50, p95, outliers
   - **Token usage**: spot excessive consumption
   - **Time patterns**: correlate with deployments or traffic spikes

## Key Parameters

- Useful filters: `status = 'ERROR'`, `status = 'OK'`
- Default max_results: 20-50 for overview, 100+ for statistical analysis

## When to Use Code Execution

Use code execution when you need to:
- Compute aggregate statistics (mean latency, error percentage)
- Process more than 50 traces for trend analysis
- Cross-reference traces with run metrics
- Generate time-series breakdowns

## Output Format

Present findings as:

```
## Trace Summary: [agent name] (Experiment [id])

| Metric | Value |
|--------|-------|
| Total Traces | N |
| Success Rate | X% |
| Avg Latency | Yms |
| Error Count | Z |

### Recent Activity
| Timestamp | Status | Duration | Tokens |
|-----------|--------|----------|--------|
| ... | OK/ERROR | Xms | N |

### Concerns (if any)
- [Issue identified with evidence]
- [Recommended action]
```
