---
name: "compliance-export"
description: "Export qualification history and audit records as structured JSONL or CSV for GRC tools and compliance systems. Use when asked to export data for auditors, generate compliance reports, or prepare evidence for regulatory review."
---

# Compliance Export

Structured export of qualification history and audit data for external GRC tools.

## When to Use

- "Export qualification history for auditors"
- "Generate a compliance report for agent X"
- "I need CSV data for our GRC tool"
- "Prepare audit evidence for review"
- "Export all qualification decisions this quarter"

## Strategy

### Step 1: Determine export scope

Identify:
- **Agent(s)** — single agent, team's agents, or entire fleet
- **Time window** — quarter, year, or custom range
- **Format** — JSONL (default, machine-readable) or CSV (spreadsheet-friendly)
- **Content** — qualification decisions, annotation history, or both

### Step 2: Gather data from MLflow

1. `mcp_mlflow_search_traces` — traces with annotation tags (reviewed, regression)
2. `mcp_mlflow_list_runs` + `mcp_mlflow_describe_run` — evaluation run details
3. `mcp_mlflow_search_experiments` — list experiments for fleet-wide export

> **Note:** `search_logged_models` is not yet in the MLflow MCP tool set.
> For CSV export, use code execution to format the MCP JSON output.

### Step 3: Structure export records

Each record must include:

| Field | Description |
|-------|-------------|
| `timestamp` | ISO-8601 event timestamp |
| `event_type` | `qualification` / `annotation` / `registration` / `tag_change` |
| `agent_name` | Human-readable agent identifier |
| `agent_model_id` | MLflow LoggedModel ID |
| `actor` | Who performed the action |
| `verdict` | QUALIFIED / NOT QUALIFIED / NEEDS REVIEW (if applicable) |
| `scorer_profile` | Evaluation profile used |
| `pass_rate` | Aggregate pass rate |
| `sample_size` | Number of traces evaluated |
| `details` | Free-form details or rationale |

### Step 4: Generate export file

Use code execution to write the structured data:
- **JSONL**: one JSON object per line, UTF-8 encoded
- **CSV**: header row + data rows, RFC 4180 compliant

Save to `/sandbox/output/` with a descriptive filename.

## Output Format

```
## Compliance Export
### Scope: [agent_name or "Fleet"] | Period: [start] — [end]
### Format: [JSONL/CSV] | Records: [N]

Export saved to: `/sandbox/output/compliance-export-[agent]-[date].[jsonl|csv]`

### Sample Record
{
  "timestamp": "2026-07-15T10:30:00Z",
  "event_type": "qualification",
  "agent_name": "outreach-agent",
  "agent_model_id": "lm-abc123",
  "actor": "agent-lens",
  "verdict": "QUALIFIED",
  "scorer_profile": "RAG",
  "pass_rate": 0.92,
  "sample_size": 200,
  "details": "All required scorers PASS, error rate 2%"
}

### Export Summary
| Event Type | Count |
|------------|-------|
| Qualification | 8 |
| Annotation | 23 |
| Registration | 3 |
| Total | 34 |
```

## Constraints

- All data sourced from MLflow MCP — no fabricated records
- JSONL is the default format for machine consumption
- CSV must be RFC 4180 compliant (quoted fields, proper escaping)
- Timestamps always ISO-8601 UTC
- Filenames must include agent identifier and date for traceability
- Never include raw trace content — only metadata and verdicts
- Never `import mlflow` in the sandbox
