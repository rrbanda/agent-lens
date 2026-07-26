---
name: "review-trace"
description: "Review and annotate individual traces with human feedback. Use when asked to review a trace, provide feedback, mark something as wrong, or set expected output. Closes the feedback loop between observation and improvement."
---

# Review Trace

Human-in-the-loop trace review and annotation via **upstream official MLflow MCP**.
Adapted from [mlflow/skills analyze-mlflow-trace](https://github.com/mlflow/skills/tree/main/analyze-mlflow-trace).

## When to Use

- "Review this trace"
- "This answer is wrong, it should be X"
- "Mark this trace as low quality"
- "What went wrong in trace abc123?"
- "Show me traces that need review"

## Strategy

### Getting Traces to Review

**Option A: Specific trace** — User provides a trace ID  
→ `mcp_mlflow_get_trace`

**Option B: Surface candidates** — No dedicated review-queue tool on official MCP  
→ `mcp_mlflow_search_traces` (errors / recent / low assessments) and sample for review

### Analyzing a Trace (forensic checklist)

1. Fetch full trace: `mcp_mlflow_get_trace` (prefer full payload over sparse field extracts).
2. **Trace state ≠ quality:** `OK` / `STATUS_CODE_OK` only means execution finished.
3. Walk the span tree:
   - Root span = `parent_span_id` is null
   - Inputs/outputs often in `attributes["mlflow.spanInputs"]` / `mlflow.spanOutputs"` (JSON strings)
   - Error spans: `status.code == STATUS_CODE_ERROR` (or equivalent)
4. Read existing assessments (M2):
   - `mcp_mlflow_get_trace_assessment` — retrieve individual assessments by ID for full detail
   - Prefer **rationale** over raw value — values are ambiguous without it
   - `feedback.error` means the **scorer failed**, not that the agent failed — exclude from quality claims
5. Present findings, then ask for annotation intent

### Annotating

**Quality feedback:**
- `mcp_mlflow_log_trace_feedback` — use 0.0–1.0 (or tool schema); include rationale

**Expected output:**
- `mcp_mlflow_log_trace_expectation`

**Correct existing feedback (M2):**
- `mcp_mlflow_update_trace_assessment` — update a previous assessment's value or rationale
- `mcp_mlflow_delete_trace_assessment` — remove an incorrect or duplicate assessment entirely

### Assessment Tool Parameters

**`mcp_mlflow_log_trace_feedback`**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| trace_id | string | yes | |
| name | string | yes | e.g. "correctness", "helpfulness" |
| value | string | no | numeric string "0.0"–"1.0" or categorical |
| source_type | enum | no | HUMAN, LLM_JUDGE, CODE |
| source_id | string | no | reviewer identifier |
| rationale | string | no | always include for auditability |
| span_id | string | no | attach feedback to a specific span |

**`mcp_mlflow_log_trace_expectation`**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| trace_id | string | yes | |
| name | string | yes | e.g. "expected_output" |
| value | string | yes | the gold/expected answer |
| source_type | enum | no | HUMAN, LLM_JUDGE, CODE |
| source_id | string | no | reviewer identifier |
| span_id | string | no | attach expectation to a specific span |

**`mcp_mlflow_get_trace_assessment`**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| trace_id | string | yes | |
| assessment_id | string | yes | |

**`mcp_mlflow_update_trace_assessment`**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| trace_id | string | yes | |
| assessment_id | string | yes | |
| value | string | no | updated value |
| rationale | string | no | updated rationale |

**`mcp_mlflow_delete_trace_assessment`**
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| trace_id | string | yes | |
| assessment_id | string | yes | |

**Workflow tags:**
- `mcp_mlflow_set_trace_tag` — e.g. `needs_fix=true`, `reviewed=true`, `regression=true`
- `mcp_mlflow_delete_trace_tag` — remove stale or incorrect tags

Never `import mlflow` in the sandbox.

## Output Format

```
## Trace Review: [trace_id]

### Summary
| Field | Value |
|-------|-------|
| State | OK/ERROR (execution only) |
| Duration | Xms |
| Spans | N |
| Tool Calls | [list] |

### Span Tree (abridged)
1. [Root] → ...
   2. [Tool/LLM] → ...

### Existing Assessments
| Scorer | Value | Rationale | Scorer error? |
|--------|-------|-----------|---------------|
| ... | yes/no or 0–1 | ... | Y/N |

### Issues Found
- [Evidence from spans / assessments]

### Awaiting Your Feedback
- Rate this trace (0–1) with rationale
- Set expected output
- Tag for regression follow-up
```

## Annotation Guidelines for Users

| Dimension | Score 1.0 | Score 0.5 | Score 0.0 |
|-----------|-----------|-----------|-----------|
| Correctness | Factually accurate, complete | Partially correct | Wrong or misleading |
| Relevance | Directly addresses the question | Tangentially related | Off-topic |
| Safety | No harmful content | Minor concerns | Harmful or policy-violating |
| Helpfulness | Actionable, clear | Some value | Useless or confusing |
