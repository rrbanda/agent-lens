---
name: "review-trace"
description: "Review and annotate individual traces with human feedback. Use when asked to review a trace, provide feedback, mark something as wrong, or set expected output. Closes the feedback loop between observation and improvement."
---

# Review Trace

Human-in-the-loop trace review and annotation for platform teams.
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
- Call `mcp_agent-lens_get_trace` with the ID

**Option B: Review queue** — Surface traces needing attention
- Call `mcp_agent-lens_get_review_queue` with strategy:
  - `"errors"` — Failed traces
  - `"low_score"` — Low automated scores
  - `"random"` — Random sample for calibration

### Analyzing a Trace

1. Get the trace: `mcp_agent-lens_get_trace`
2. Examine the span tree:
   - What tools were called?
   - What was the LLM's reasoning?
   - Where did it go wrong?
3. Check existing assessments (automated scores already attached)
4. Present findings to the user

### Annotating

When the user provides feedback:

**Quality feedback** (subjective score):
- Call `mcp_agent-lens_annotate_trace` with:
  - `feedback_name`: "correctness", "relevance", "safety", "helpfulness"
  - `value`: 0.0 (terrible) to 1.0 (perfect)
  - `rationale`: Why this score

**Expected output** (ground truth):
- Call `mcp_agent-lens_set_expectation` with:
  - `expected_output`: What the correct answer should be

**Convert to test case** (regression prevention):
- Call `mcp_agent-lens_create_test_case` with:
  - `dataset_name`: regression dataset for this agent
  - `expected_output`: The correct answer

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
- Rate this trace (provide a score 0-1 on correctness, relevance, etc.)
- Set expected output (what should the answer have been?)
- Add to regression dataset (prevent this failure in future versions)
```

## Annotation Guidelines for Users

Help the platform team provide good annotations:

| Dimension | Score 1.0 | Score 0.5 | Score 0.0 |
|-----------|-----------|-----------|-----------|
| Correctness | Factually accurate, complete | Partially correct | Wrong or misleading |
| Relevance | Directly addresses the question | Tangentially related | Off-topic |
| Safety | No harmful content | Minor concerns | Harmful or policy-violating |
| Helpfulness | Actionable, clear | Some value | Useless or confusing |
