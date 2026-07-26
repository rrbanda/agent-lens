---
name: "quality-dashboard"
description: "Generate a full observability summary across all tracked agents: top experiments, recent runs, health scores, and alerts. Use when asked for an overview or 'how are things going' type questions."
---

# Quality Dashboard

Fleet-wide observability summary for agent platform engineers across all tracked agents via **upstream official MLflow MCP**.
Based on [MLflow Cookbook: Production Observability with MLflow Tracing](https://mlflow.org/cookbook/production-observability/).

Quality from GenAI scorers is a **pass rate** (yes/no), not a 1–5 Likert. Prefer error rate +
latency for health when evaluation metrics are absent.

## Strategy (MCP-first — required)

1. Call `mcp_mlflow_search_experiments` to list active experiments (agents).
2. Cap the fleet scan at **20 experiments** (prefer recently updated). Say so in the report if truncated.
3. For each selected experiment:
   - `mcp_mlflow_search_traces` with that experiment id (`max_results` 50)
   - Optionally `mcp_mlflow_list_runs` for recent evaluation metrics / pass rates
4. Extract operational metrics from trace data following the cookbook's exact patterns:
   - **Error rate**: `sum(1 for t in traces if t.info.status == "ERROR") / len(traces) * 100`
   - **Latency**: sort `execution_time_ms` values, compute `p50 = latencies[len//2]`, `p95 = latencies[int(len*0.95)]`
   - **Token usage**: from `trace.info.token_usage` (dict with `input_tokens`, `output_tokens`)
     or `trace.info.request_metadata["mlflow.trace.tokenUsage"]` (JSON string)
   - **Throughput**: traces per hour from trace timestamps
5. Compute status with the criteria table (code execution may aggregate MCP JSON only).
6. Format the Observatory output below.

Do **not** open code execution to call MLflow. Only use it on data already returned by MCP.

## Anti-patterns (never do this)

> **Do not** `import mlflow`, call `mlflow.set_tracking_uri`, or connect to an MLflow
> database / tracking server from the Hermes code-execution sandbox. That environment
> has no ServiceAccount token to the MLflow tracking server and will hang or fail. All MLflow access
> must go through official MCP tools (`mcp_mlflow_*`).

## Health Status Criteria

| Status | Conditions |
|--------|-----------|
| HEALTHY | Has traces; error rate < 5%; if eval metrics exist, primary pass rate >= 80% |
| WARNING | Error rate 5–15%; or active with traces but no eval scores; or pass rate 50–80% |
| CRITICAL | Error rate > 15%; or pass rate < 50%; or MCP tool error fetching data |
| INACTIVE | No traces recorded in the experiment |

Do **not** use `/5` quality scores. If only categorical assessments exist, convert to pass rate.

## Output Format

```
## AI Agent Observatory
Generated: [timestamp]
Scan cap: N experiments (truncated: yes/no)

### Fleet Summary
| Status | Count |
|--------|-------|
| Healthy | N |
| Warning | N |
| Critical | N |
| Inactive | N |

### Fleet Operational Metrics
| Metric | Fleet Total | Fleet Average |
|--------|-------------|---------------|
| Total Traces (sample) | N | N/agent |
| Throughput | N traces/hr | N/agent/hr |
| Avg Latency (p50) | — | Xms |
| Avg Latency (p95) | — | Xms |
| Est. Token Cost (24h) | $X.XX | $X.XX/agent |

---

### [Agent Name] (Experiment [id]) — [STATUS]
| Metric | Value | Trend |
|--------|-------|-------|
| Traces (sample) | N | up/down/stable |
| Error Rate | X% | up/down/stable |
| Latency (p50) | Xms | up/down/stable |
| Latency (p95) | Xms | up/down/stable |
| Throughput | N/hr | up/down/stable |
| Token Cost (est.) | $X.XX/trace | up/down/stable |
| Eval pass rate | XX% or n/a | up/down/stable |

---

### Alerts
| Severity | Agent | Issue |
|----------|-------|-------|
| CRITICAL | ... | ... |
| WARNING | ... | ... |

### Cost Hotspots
| Agent | Est. Cost/Trace | Traces/Day | Est. Daily Cost |
|-------|----------------|------------|-----------------|
| [most expensive] | $X.XXX | N | $X.XX |
| [second] | $X.XXX | N | $X.XX |

### Recommended Actions
1. [Most urgent — backed by data]
2. [Second priority]
3. [Optimization opportunity — e.g., cost reduction via `cost-quality` skill]
```

## Token Cost Extraction

From the [Production Observability Cookbook](https://mlflow.org/cookbook/production-observability/),
token usage is in two possible locations:

**Primary (MLflow 3.x):** `trace.info.token_usage`
```json
{"input_tokens": 420, "output_tokens": 690, "total_tokens": 1110}
```

**Fallback (earlier versions):** `trace.info.request_metadata["mlflow.trace.tokenUsage"]`
(JSON string, parse it first)

To sum across traces (from the cookbook's pattern):
- total_input = sum of `usage.input_tokens` across all traces
- total_output = sum of `usage.output_tokens` across all traces

If cost data is unavailable for an agent, show "n/a" and recommend enabling MLflow autolog
(`mlflow.openai.autolog()` or equivalent).
Never fabricate cost numbers.

## Throughput Calculation

Compute from trace timestamps within the sample:
- `throughput = num_traces / (latest_timestamp - earliest_timestamp) * 3600`
- If all traces are from same second, report "burst" not hourly rate
- Use "traces/hr" as the unit

When status is INACTIVE, recommend instrumentation (`usercustomize.py` / MLflow autolog)
and optionally running `evaluate-agent` after traces exist — do not claim a configuration
error if MCP tools succeeded with empty traces.
