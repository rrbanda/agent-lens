---
name: "evaluate-agent"
description: "Run a systematic evaluation of any agent's quality using MLflow GenAI scorers. Use when asked to evaluate, score, certify, or assess an agent's performance. Produces a Quality Certification Report."
---

# Evaluate Agent

Systematic agent evaluation for platform teams via **upstream official MLflow MCP**.
Adapted from [mlflow/skills agent-evaluation](https://github.com/mlflow/skills/tree/main/agent-evaluation).

MLflow GenAI built-in scorers return **categorical yes/no** (or equivalent), not a 1–5 Likert.
Report **pass rates** (share of traces scoring yes / positive). Never invent `/5` scores.

## When to Use

- "Evaluate Agent X"
- "How good is the outreach agent?"
- "Run a quality check before deploy"
- "Score the latest traces"
- "Is this agent ready for production?"

## Strategy

### Step 1: Identify the Agent

Call `mcp_mlflow_search_experiments` to find the target agent's experiment.

### Step 2: Agent interview (do not skip)

Confirm agent type (RAG / tool-calling / chat) and what “good” means. Derive scorers from that —
do not invent custom score names.

### Step 3: Select Scorer Profile

Confirm availability with `mcp_mlflow_list_scorers` if needed.

**RAG Agent Profile**:
- `RelevanceToQuery` — Does the output address the request?
- `RetrievalGroundedness` — Is it grounded in retrieved context?
  - **Prerequisite:** traces must include a `RETRIEVER` (or equivalent retrieval) span.
  - OpenAI-only autolog (`usercustomize.py`) often **lacks** retriever spans — warn and skip
    groundedness or mark NEEDS REVIEW rather than failing silently.

**Tool-Calling Agent Profile**:
- `ToolCallCorrectness` — Are tool calls and arguments correct?
- `ToolCallEfficiency` — No redundant or unnecessary calls?
- `RelevanceToQuery` — Does the final answer address the user?

**Chat Agent Profile**:
- `RelevanceToQuery` — Addresses the user's intent?
- Guidelines: helpful, harmless, honest

**Custom Profile** — Ask the user what dimensions matter most (`Guidelines` / registered scorers).

### Step 4: Dry run (required before full cert)

Call `mcp_mlflow_evaluate_traces` with a **small** sample first (`max_traces`: 3–5).
If scorers error, tools are broken, or all traces empty — stop and report; do not run 50–200.

### Step 5: Full evaluation

Call `mcp_mlflow_evaluate_traces` with chosen scorers:

- Quick check: `max_traces` 50
- Certification: `max_traces` 200 (follow tool schema)

**Regression-focused cert:** If the user asks to include regression follow-ups, first
`mcp_mlflow_search_traces` with tags/filter for `regression=true` (or dataset tag), evaluate
those traces preferentially, and state the sample composition in the report.

### Step 6: Generate Quality Certification Report

Aggregate MCP JSON only (optional code execution on returned data). Never `import mlflow`.

## Scoring rules

| Signal | How to report | Default threshold |
|--------|---------------|-------------------|
| Built-in GenAI scorer | Pass rate = (# yes or positive) / (# scored) | **≥ 80%** PASS |
| Trace status ERROR | Error rate on sample | **< 5%** for CERTIFIED |
| Scorer `feedback.error` | Scorer failure — exclude from pass rate; call out separately | — |

`state: OK` / `STATUS_CODE_OK` means the run completed — **not** that the answer is correct.

## Output Format

```
# Quality Certification Report
## Agent: [name] | Experiment: [id]
## Date: [timestamp] | Evaluator: Agent Lens

### Profile: [RAG/Tool-Calling/Chat]

### Scores (pass rates — GenAI yes/no scorers)
| Dimension | Pass rate | Rating | Threshold |
|-----------|-----------|--------|-----------|
| RelevanceToQuery | XX% | PASS/FAIL | >= 80% |
| RetrievalGroundedness | XX% or N/A | PASS/FAIL/SKIPPED | >= 80% |
| ToolCallCorrectness | XX% | PASS/FAIL | >= 80% |

### Certification verdict (chat — not a CI pipeline block)
**[CERTIFIED / NOT CERTIFIED / NEEDS REVIEW]**

Rules of thumb:
- CERTIFIED: all required scorers PASS and error rate < 5%
- NOT CERTIFIED: any required scorer FAIL or error rate >= 5%
- NEEDS REVIEW: missing retriever spans, scorer errors, or insufficient sample

### Evidence
- Traces evaluated: N (dry-run + full)
- Error rate: X%
- Avg latency: Xms
- Regression-tagged traces included: Y/N

### Findings (if NOT CERTIFIED / NEEDS REVIEW)
1. [Issue with evidence]
2. [Recommended action]

### Next Steps
- [ ] Address findings above
- [ ] Re-run evaluation after fixes
- [ ] Log expectations on failure traces (`create-regression` / review-trace)
```

## When to Use Code Execution

- Aggregate pass rates on data already returned by MCP
- Format comparison tables (before/after)
- Never call the MLflow tracking SDK from the sandbox
