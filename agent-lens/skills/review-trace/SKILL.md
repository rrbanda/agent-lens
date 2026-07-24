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
- Call `mcp_mlflow_get_trace` with the ID

**Option B: Surface candidates** — No dedicated review-queue tool on official MCP
- Call `mcp_mlflow_search_traces` with filters for errors / recent activity
- Optionally sort or sample from returned results for review

### Analyzing a Trace

1. Get the trace: `mcp_mlflow_get_trace`
2. Examine the span tree:
   - What tools were called?
   - What was the LLM's reasoning?
   - Where did it go wrong?
3. Check existing assessments (automated scores already attached)
4. Present findings to the user

### Annotating

When the user provides feedback:

**Quality feedback** (subjective score):
- Call `mcp_mlflow_log_trace_feedback` with name, value, and rationale
  (follow tool schema — e.g. correctness / relevance / safety / helpfulness)

**Expected output** (ground truth):
- Call `mcp_mlflow_log_trace_expectation` with the expected output

**Workflow tags**:
- Call `mcp_mlflow_set_trace_tag` (e.g. `needs_fix=true`, `reviewed=true`)

Never `import mlflow` in the sandbox.

## Output Format

```
## Trace Review: [trace_id]

### Summary
| Field | Value |
|-------|-------|
| Status | OK/ERROR |
| Duration | Xms |
| Spans | N |
| Tool Calls | [list] |

### Span Tree
1. [Root] → LLM call (Xms)
   2. [Tool] → search_documents (Yms)
   3. [Tool] → format_response (Zms)

### Existing Assessments
| Scorer | Score | Source |
|--------|-------|--------|
| RelevanceToQuery | X.X | LLM judge |

### Issues Found
- [Issue description with evidence from spans]

### Awaiting Your Feedback
What would you like to do?
- Rate this trace (provide a score on correctness, relevance, etc.)
- Set expected output (what should the answer have been?)
- Tag for follow-up / regression tracking
```

## Annotation Guidelines for Users

| Dimension | Score 1.0 | Score 0.5 | Score 0.0 |
|-----------|-----------|-----------|-----------|
| Correctness | Factually accurate, complete | Partially correct | Wrong or misleading |
| Relevance | Directly addresses the question | Tangentially related | Off-topic |
| Safety | No harmful content | Minor concerns | Harmful or policy-violating |
| Helpfulness | Actionable, clear | Some value | Useless or confusing |
