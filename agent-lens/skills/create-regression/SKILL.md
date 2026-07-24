---
name: "create-regression"
description: "Log a regression follow-up on a failing trace (expectation + tags). Use when asked to add a test case, create a regression, or ensure a bug doesn't happen again. Does not create an MLflow Evaluation Dataset."
---

# Create Regression Follow-up

Failure-to-follow-up via **upstream official MLflow MCP**.
Official MCP has no dataset create API — capture ground truth with expectations + tags.
Adapted in spirit from [mlflow/skills fix-agent-issue](https://github.com/mlflow/skills/tree/main/fix-agent-issue) (observe/annotate only — Agent Lens does not patch target agent code).

## When to Use

- "Add this to the regression dataset"
- "Make sure this never happens again"
- "Create a test case from this failure"
- After reviewing a trace and identifying what went wrong

## Strategy

### Step 1: Identify the Failing Trace

User provides `trace_id`, or find via `mcp_mlflow_search_traces` (ERROR / low score).

### Step 2: Extract the Case

From `mcp_mlflow_get_trace`:
- **Input** — user query/request
- **Expected output** — user-confirmed correct answer
- **Context** (RAG) — documents available, if any

### Step 3: Persist via official MCP

1. `mcp_mlflow_log_trace_expectation` with confirmed expected output
2. `mcp_mlflow_set_trace_tag`:
   - `regression=true`
   - `dataset=<agent-name>-regression` (naming convention)
3. Optionally `mcp_mlflow_log_trace_feedback` if a quality score was given

### Step 4: Confirm and advise

Tell the user:
1. Expectation + tags logged
2. Next **evaluate-agent** run should request a **regression-focused cert** so tagged traces are prioritized
3. For a durable GenAI Evaluation Dataset, export/create records in MLflow UI/SDK outside the sandbox

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

### Next Steps
- Run evaluate-agent with regression-focused sample
- Add 2–3 related variations on sibling traces if needed
```

## Dataset Naming Convention

| Agent Type | Dataset Name |
|-----------|-------------|
| Outreach agent | `outreach-agent-regression` |
| Support agent | `support-agent-regression` |
| Generic | `{agent-name}-regression` |
