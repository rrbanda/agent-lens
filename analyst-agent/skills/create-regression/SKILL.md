---
name: "create-regression"
description: "Convert production failures into regression test cases that prevent the same issue from recurring. Use when asked to add a test case, create a regression, or ensure a bug doesn't happen again."
---

# Create Regression Test

The failure-to-dataset pipeline: production failures become permanent test cases.
This is what closes the AgentOps feedback loop.

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
- From error search: `mcp_agent-lens_search_traces` with filter `trace.status = "ERROR"`
- From low-score search: `mcp_agent-lens_get_review_queue`

### Step 2: Extract the Test Case

From the trace, extract:
- **Input**: What was the user's query/request?
- **Expected output**: What should the agent have produced?
- **Context** (if RAG): What documents were available?

The user must confirm the expected output (or provide it).

### Step 3: Add to Dataset

Call `mcp_agent-lens_create_test_case` with:
- `trace_id`: The source trace
- `dataset_name`: Agent's regression dataset (convention: `{agent-name}-regression`)
- `expected_output`: The correct answer

### Step 4: Confirm and Advise

Tell the user:
1. Test case was added
2. Next eval run will include it
3. If the agent regresses on this case, it will show in the Quality Gate

## Output Format

```
## Regression Test Created

| Field | Value |
|-------|-------|
| Source Trace | [trace_id] |
| Dataset | [dataset_name] |
| Input | [extracted query] |
| Expected | [user-provided expected output] |

### Impact
This test case will:
- Be included in all future evaluations of [agent name]
- Block deployment if the agent fails this case (via quality gate)
- Appear in the Quality Certification Report

### Dataset Status
| Metric | Value |
|--------|-------|
| Total test cases | N |
| Added today | +1 |
| Coverage areas | [list] |

### Next Steps
- Run `evaluate-agent` to verify the current version passes
- Consider adding 2-3 related variations to catch similar failures
```

## Dataset Naming Convention

| Agent Type | Dataset Name |
|-----------|-------------|
| Outreach agent | `outreach-agent-regression` |
| Support agent | `support-agent-regression` |
| Code agent | `code-agent-regression` |
| Generic | `{agent-name}-regression` |

## Best Practices

- Each test case should test ONE thing (not compound failures)
- Expected outputs should be specific enough to score against
- Add variations: if "query about X" failed, also test "query about Y" (related)
- 50-100 test cases is a good target per agent
- Review and prune the dataset quarterly (remove obsolete cases)
