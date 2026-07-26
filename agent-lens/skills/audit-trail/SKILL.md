---
name: "audit-trail"
description: "Query and display structured audit records of qualification decisions, annotations, and agent lifecycle events. Use when asked about audit history, compliance evidence, decision trail, or who approved what and when."
---

# Audit Trail

Structured, queryable record of all Agent Lens qualification decisions and annotations.

## When to Use

- "Show me the audit trail for agent X"
- "Who qualified this agent and when?"
- "What changed since last qualification?"
- "Show all qualification decisions this month"
- "Export compliance evidence for this agent"

## Strategy

### Step 1: Identify scope

Determine what the user wants to audit:
- **Single agent** — qualification history for one agent
- **Time window** — all events in a date range
- **Event type** — only qualifications, only annotations, only tag changes

### Step 2: Gather evidence from MLflow

Agent Lens audit records are derived from MLflow data:

1. **Annotation events** — `mcp_mlflow_search_traces` filtered by tags (`reviewed=true`, `regression=true`) to find annotated traces
2. **Evaluation runs** — `mcp_mlflow_list_runs` + `mcp_mlflow_describe_run` for evaluation run metadata (who ran it, when, which scorers)
3. **Experiment context** — `mcp_mlflow_search_experiments` to resolve experiment names

> **Note:** `search_logged_models` is not yet in the MLflow MCP tool set.
> Reconstruct qualification events from evaluation run metadata and tags.

### Step 3: Reconstruct timeline

Build a chronological timeline of events from the gathered data:
- Qualification verdicts (QUALIFIED / NOT QUALIFIED / NEEDS REVIEW)
- Annotation actions (feedback logged, expectations set)
- Tag changes (regression flags, review status)

### Step 4: Present structured audit view

## Output Format

```
## Audit Trail: [agent_name]
### Period: [start_date] — [end_date]

| Timestamp | Event | Actor | Details |
|-----------|-------|-------|---------|
| 2026-07-15T10:30Z | QUALIFIED | Agent Lens | Pass rate 92%, RAG profile, 200 traces |
| 2026-07-10T14:00Z | Annotation | user@example.com | Trace abc123: feedback=0.0, "hallucinated source" |
| 2026-07-08T09:15Z | Regression tagged | user@example.com | Trace def456: regression=true |

### Summary
- Total events: N
- Qualifications: N (QUALIFIED: X, NOT QUALIFIED: Y)
- Annotations: N
- Pending reviews: N
```

## Constraints

- Derive all data from MLflow MCP — do not fabricate audit entries
- Timestamps must be ISO-8601
- Cap queries at 100 events per request; paginate if more exist
- Never `import mlflow` in the sandbox
