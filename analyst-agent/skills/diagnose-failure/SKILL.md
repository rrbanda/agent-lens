---
name: "diagnose-failure"
description: "Given a trace ID, time range, or symptom description, analyze what went wrong in an agent interaction. Use when asked about errors, failures, slow responses, or quality drops."
---

# Diagnose Failure

Root-cause analysis of agent failures, errors, or quality degradation.

## Strategy

1. Scope the investigation:
   - Specific trace — call `mcp_mlflow_search_traces` with filter
   - Error pattern — search traces with `status = 'ERROR'`
   - Quality drop — search recent runs and compare scores
2. Gather evidence — correlate traces with runs and metrics
3. Identify root cause using common failure taxonomy
4. Tag trace if actionable — call `mcp_mlflow_set_trace_tag`

## Common Failure Taxonomy

| Pattern | Symptoms | Root Cause | Fix |
|---------|----------|-----------|-----|
| Timeout | Latency > 30s, status ERROR | Model overloaded or cold start | Smaller model, warmup, or retry |
| Rate limit | Multiple 429 errors in traces | Too many concurrent requests | Backoff, queue, reduce concurrency |
| Bad RAG | Low relevance, correct LLM output | Stale or misindexed vector DB | Reindex, check embedding model |
| Hallucination | High relevance, low faithfulness | Weak grounding in prompt | Add "cite only from context" |
| Token overflow | Errors on long inputs | Input exceeds context window | Chunking, summarization |
| Empty response | Status OK but no output | Tool call failed silently | Check tool response handling |

## When to Use Code Execution

Use code execution when:
- Analyzing error patterns across many traces (grouping, counting)
- Computing time-correlation between errors and deployments
- Building a timeline from multiple trace spans

## Output Format

```
## Failure Diagnosis

### Scope
[What was investigated: trace ID, time range, or symptom]

### Findings
| Finding | Severity | Evidence |
|---------|----------|----------|
| [Issue] | Critical/High/Medium/Low | [Data showing this] |

### Root Cause
[Most likely explanation — 1-2 sentences with data backing]

### Timeline (if applicable)
1. [Step]: OK (Xms)
2. [Step]: SLOW (Yms) <- bottleneck
3. [Step]: ERROR — [message]

### Remediation
- **Immediate**: [What to do now]
- **Long-term**: [What to fix in the agent]
```
