---
name: "evaluate-agent"
description: "Run a systematic evaluation of any agent's quality using MLflow scorers. Use when asked to evaluate, score, certify, or assess an agent's performance. Produces a Quality Certification Report."
---

# Evaluate Agent

Systematic agent evaluation for platform teams via **upstream official MLflow MCP**.
Adapted from [mlflow/skills agent-evaluation](https://github.com/mlflow/skills/tree/main/agent-evaluation).

## When to Use

- "Evaluate Agent X"
- "How good is the outreach agent?"
- "Run a quality check before deploy"
- "Score the latest traces"
- "Is this agent ready for production?"

## Strategy

### Step 1: Identify the Agent

Call `mcp_mlflow_search_experiments` to find the target agent's experiment.

### Step 2: Select Scorer Profile

Choose based on agent type. Confirm availability with `mcp_mlflow_list_scorers` if needed.

**RAG Agent Profile**:
- `RelevanceToQuery` — Does the output address the request?
- `RetrievalGroundedness` — Is it grounded in retrieved context?

**Tool-Calling Agent Profile**:
- `ToolCallCorrectness` — Are tool calls and arguments correct?
- `ToolCallEfficiency` — No redundant or unnecessary calls?
- `RelevanceToQuery` — Does the final answer address the user?

**Chat Agent Profile**:
- `RelevanceToQuery` — Addresses the user's intent?
- Guidelines: helpful, harmless, honest

**Custom Profile** — Ask the user what dimensions matter most.

### Step 3: Run Evaluation

Call `mcp_mlflow_evaluate_traces` with the experiment / traces and chosen scorers
(`max_traces`: 50 for quick check, 200 for certification — follow tool schema).

### Step 4: Generate Quality Certification Report

Use MCP results (and optional code execution on returned JSON only) to fill the report.
Never `import mlflow` in the sandbox.

## Output Format

```
# Quality Certification Report
## Agent: [name] | Experiment: [id]
## Date: [timestamp] | Evaluator: Agent Lens

### Profile: [RAG/Tool-Calling/Chat]

### Scores
| Dimension | Score | Rating | Threshold |
|-----------|-------|--------|-----------|
| Relevance | X.X/5 | PASS/FAIL | >= 3.5 |
| Groundedness | X.X/5 | PASS/FAIL | >= 3.5 |
| Tool Correctness | X.X/5 | PASS/FAIL | >= 3.5 |

### Certification verdict (chat — not a CI pipeline block)
**[CERTIFIED / NOT CERTIFIED / NEEDS REVIEW]**

### Evidence
- Traces evaluated: N
- Error rate: X%
- Avg latency: Xms

### Findings (if NOT CERTIFIED)
1. [Issue with evidence]
2. [Recommended action]

### Next Steps
- [ ] Address findings above
- [ ] Re-run evaluation after fixes
- [ ] Log expectations on failure traces for regression follow-up
```

## When to Use Code Execution

- Aggregate stats on data already returned by MCP
- Format comparison tables (before/after)
- Never call the MLflow tracking SDK from the sandbox
