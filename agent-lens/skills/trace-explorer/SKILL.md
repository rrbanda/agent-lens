---
name: "trace-explorer"
description: "Search and summarize traces from any agent's MLflow experiment. Shows latency, token usage, error rates, and interaction patterns. Use when asked about recent agent activity or trace details."
---

# Trace Explorer

Investigate agent activity by querying trace data via **upstream official MLflow MCP**.

## Strategy

1. Identify the target experiment — call `mcp_mlflow_search_experiments` if unknown
2. Search traces — call `mcp_mlflow_search_traces` with the experiment_id
3. For detail on a single trace — call `mcp_mlflow_get_trace`
4. Analyze for patterns:
   - **Error rate**: count ERROR status vs total
   - **Latency distribution**: identify p50, p95, outliers
   - **Token usage**: spot excessive consumption
   - **Time patterns**: correlate with deployments or traffic spikes

## Key Parameters

- Useful filters: `status = 'ERROR'`, `status = 'OK'` (follow tool schema)
- Default max_results: 20-50 for overview, 100+ for statistical analysis

## When to Use Code Execution

Use code execution when you need to:
- Compute aggregate statistics on MCP-returned JSON (mean latency, error %)
- Process large payloads already fetched via MCP
- Generate time-series breakdowns from local data

Never `import mlflow` in the sandbox — use `mcp_mlflow_*` only.

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
