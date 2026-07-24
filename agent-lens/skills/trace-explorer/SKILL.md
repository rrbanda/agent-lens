---
name: "trace-explorer"
description: "Search and summarize traces from any agent's MLflow experiment. Shows latency, token usage, error rates, and interaction patterns. Use when asked about recent agent activity or trace details."
---

# Trace Explorer

Investigate agent activity via **upstream official MLflow MCP**.
Adapted from [mlflow/skills retrieving-mlflow-traces](https://github.com/mlflow/skills/tree/main/retrieving-mlflow-traces).

## Strategy

1. Identify experiment — `mcp_mlflow_search_experiments` if unknown
2. Search — `mcp_mlflow_search_traces` (follow tool schema for filters)
3. Detail — `mcp_mlflow_get_trace` for a single ID
4. Analyze: error rate, latency distribution, token usage, time patterns

## Filter cookbook (adapt to MCP schema)

Prefer schema-accurate filters such as:

- Execution failures: `trace.status = 'ERROR'` (or tool-equivalent)
- Session: metadata key `mlflow.trace.session` (dots — quoting rules vary)
- Tags: `regression=true` for follow-up samples
- Time / latency: use fields exposed by the MCP tool description

Default `max_results`: 20–50 overview; 100+ for stats.

Never `import mlflow` in the sandbox.

## Output Format

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

### Concerns
- [Issue with evidence]
```
