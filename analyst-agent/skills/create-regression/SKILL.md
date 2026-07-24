---
name: "create-regression"
description: "Log a regression follow-up on a failing trace (expectation + tags). Use when asked to add a test case, create a regression, or ensure a bug doesn't happen again. Does not create an MLflow Evaluation Dataset."
---

# Create Regression Test

Failure-to-follow-up via **upstream official MLflow MCP**.
Official MCP does not expose dataset APIs — capture ground truth with expectations + tags,
and advise the user how to promote into an eval dataset offline if needed.

## When to Use

- "Add this to the regression dataset"
- "Make sure this never happens again"
- "Create a test case from this failure"
- "This trace should be in our eval suite"
- After reviewing a trace and identifying what went wrong

## Strategy

### Step 1: Identify the Failing Trace

Either the user provides a trace_id, or find one:
- From a review session (review-trace skill)
- From error search: `mcp_mlflow_search_traces` with filter for ERROR status

### Step 2: Extract the Test Case

From the trace (`mcp_mlflow_get_trace`), extract:
- **Input**: What was the user's query/request?
- **Expected output**: What should the agent have produced?
- **Context** (if RAG): What documents were available?

The user must confirm the expected output (or provide it).

### Step 3: Persist via official MCP

1. Call `mcp_mlflow_log_trace_expectation` with the confirmed expected output
2. Call `mcp_mlflow_set_trace_tag` with tags such as:
   - `regression=true`
   - `dataset=<agent-name>-regression` (naming convention)
3. Optionally `mcp_mlflow_log_trace_feedback` if a quality score was given

### Step 4: Confirm and Advise

Tell the user:
1. Expectation + tags were logged on the trace
2. Next `evaluate-agent` run can include / prioritize tagged traces
3. For a durable GenAI evaluation dataset, export or create records in MLflow UI / SDK outside the sandbox (official MCP has no `create_dataset` tool)

Never `import mlflow` in the sandbox.

## Output Format

```
## Regression Follow-up Logged

| Field | Value |
|-------|-------|
| Source Trace | [trace_id] |
| Dataset tag | [dataset_name] |
| Input | [extracted query] |
| Expected | [user-provided expected output] |

### Impact
- Ground-truth expectation is attached to the trace
- Trace is tagged for regression tracking
- Future evaluations can prioritize tagged failures

### Next Steps
- Run `evaluate-agent` to verify the current version
- Consider adding 2-3 related variations (annotate sibling traces)
```

## Dataset Naming Convention

| Agent Type | Dataset Name |
|-----------|-------------|
| Outreach agent | `outreach-agent-regression` |
| Support agent | `support-agent-regression` |
| Code agent | `code-agent-regression` |
| Generic | `{agent-name}-regression` |

## Best Practices

- Each case should test ONE thing (not compound failures)
- Expected outputs should be specific enough to score against
- Add variations: if "query about X" failed, also test related Y
- Review and prune tagged regressions quarterly
