---
name: "aggregate-traces"
description: "Compute aggregate metrics from traces — error rates, latency percentiles, token usage, and quality trends over configurable time windows. Use when asked about agent performance over time, operational health, or fleet-level metrics."
---

# Aggregate Traces

Operational metrics aggregation from MLflow traces over configurable time windows.

## When to Use

- "What's the error rate for agent X this week?"
- "Show me latency percentiles for the last 30 days"
- "How many tokens is agent Y consuming?"
- "Give me a health summary for the past 24 hours"
- "Compare this week vs last week"

## Strategy

### Step 1: Determine scope

Identify:
- **Agent(s)** — single agent or fleet-wide
- **Time window** — 24h, 7d, 30d, or custom range
- **Metrics** — error rate, latency, token usage, trace volume, or all

### Step 2: Fetch traces

`mcp_mlflow_search_traces` — retrieve traces within the time window.

Batch as needed: MLflow returns pages, so issue multiple calls for large windows. Cap at 1000 traces per aggregation to keep computation bounded.

### Step 3: Compute aggregations (code execution)

Use code execution on the returned MCP JSON to compute:

- **Error rate**: count of `STATUS_CODE_ERROR` / total traces
- **Latency**: p50, p95, p99 from trace duration fields
- **Token usage**: sum input/output tokens from span attributes
- **Trace volume**: count per hour/day for trend lines
- **Quality scores**: aggregate pass rates from assessments (if present)

### Step 4: Present results

## Output Format

```
## Trace Aggregation: [agent_name]
### Window: [start] — [end] | Traces: [N]

### Health Metrics
| Metric | Value | Trend |
|--------|-------|-------|
| Error rate | 3.2% | ↓ from 5.1% last period |
| Latency p50 | 1,200ms | → stable |
| Latency p95 | 4,800ms | ↑ from 3,900ms |
| Token usage (total) | 1.2M tokens | ↑ 15% |
| Trace volume | 4,200 traces | → stable |

### Quality (from assessments)
| Scorer | Pass rate | Sample size |
|--------|-----------|-------------|
| RelevanceToQuery | 88% | 150 traces |
| RetrievalGroundedness | 82% | 120 traces |

### Anomalies
- Latency p95 spike on 2026-07-20 (8,200ms) — correlates with 3 timeout errors
- Error rate elevated 2026-07-18 to 2026-07-19 (12%) — resolved
```

## Time Windows

| Shorthand | Duration | Typical use |
|-----------|----------|-------------|
| 24h | Last 24 hours | Incident triage |
| 7d | Last 7 days | Weekly standup |
| 30d | Last 30 days | Monthly review |
| custom | User-specified | Compliance, audit |

## Constraints

- Cap at 1000 traces per aggregation — warn if window yields more
- Code execution for math only — never `import mlflow`
- Latency = trace duration, not wall clock (respect what MLflow records)
- Token counts depend on span attributes — warn if instrumentation does not capture them
