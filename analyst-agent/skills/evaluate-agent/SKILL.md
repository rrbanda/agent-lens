---
name: "evaluate-agent"
description: "Run a systematic evaluation of any agent's quality using MLflow scorers. Use when asked to evaluate, score, certify, or assess an agent's performance. Produces a Quality Certification Report."
---

# Evaluate Agent

Systematic agent evaluation for platform teams. Adapted from [mlflow/skills agent-evaluation](https://github.com/mlflow/skills/tree/main/agent-evaluation).

## When to Use

- "Evaluate Agent X"
- "How good is the outreach agent?"
- "Run a quality check before deploy"
- "Score the latest traces"
- "Is this agent ready for production?"

## Strategy

### Step 1: Identify the Agent

Call `mcp_agent-lens_list_experiments` to find the target agent's experiment.

### Step 2: Select Scorer Profile

Choose based on agent type:

**RAG Agent Profile** (retrieval-augmented generation):
- `RelevanceToQuery` — Does the output address the request?
- `RetrievalGroundedness` — Is it grounded in retrieved context?
- Guidelines: "The response must cite sources from the retrieved documents"

**Tool-Calling Agent Profile** (function calling, API agents):
- `ToolCallCorrectness` — Are tool calls and arguments correct?
- `ToolCallEfficiency` — No redundant or unnecessary calls?
- `RelevanceToQuery` — Does the final answer address the user?

**Chat Agent Profile** (conversational assistants):
- `RelevanceToQuery` — Addresses the user's intent?
- Guidelines: "Response is helpful, harmless, and honest"
- Guidelines: "Response maintains conversation context"

**Custom Profile** — Ask the user what dimensions matter most.

### Step 3: Run Evaluation

Call `mcp_agent-lens_run_evaluation` with:
- `experiment_id`: from step 1
- `scorer_names`: from step 2 profile
- `max_traces`: 50 for quick check, 200 for certification

### Step 4: Generate Quality Certification Report

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

### Certification
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
- [ ] Add failure cases to regression dataset
```

## When to Use Code Execution

- Computing aggregate stats across many traces
- Generating time-series quality trends
- Cross-referencing multiple evaluation runs
- Producing comparison reports (before/after)
