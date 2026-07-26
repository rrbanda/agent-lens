---
name: "evaluate-agent"
description: "Run a systematic evaluation of any agent's quality using MLflow GenAI scorers. Use when asked to evaluate, score, qualify, or assess an agent's performance. Produces a Quality Qualification Report."
---

# Evaluate Agent

Systematic agent evaluation for agent platform engineers via **upstream official MLflow MCP**.
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

**Registering custom scorers:** Use `mcp_mlflow_register_llm_judge_scorer` to register a custom LLM judge scorer with specific instructions for domain-specific evaluation. Verify availability with `mcp_mlflow_list_scorers` before using in evaluation.

**`mcp_mlflow_register_llm_judge_scorer` parameters:**
- `name` (string, required) — unique scorer name
- `instructions` (string, required) — judging instructions; must contain template variables like `{{ inputs }}`, `{{ outputs }}`
- `experiment_id` (string, required) — experiment to register the scorer under

### Step 4: Dry run (required before full cert)

Call `mcp_mlflow_evaluate_traces` with a **small** sample first (`max_traces`: 3–5).
If scorers error, tools are broken, or all traces empty — stop and report; do not run 50–200.

### Step 5: Full evaluation

Call `mcp_mlflow_evaluate_traces` with chosen scorers:

- Quick check: `max_traces` 50
- Qualification: `max_traces` 200

**`mcp_mlflow_evaluate_traces` parameters:**
- `experiment_id` (string, required) — target experiment
- `trace_ids` (string, required) — comma-separated trace IDs to evaluate
- `scorers` (string, required) — comma-separated scorer names (e.g. `RelevanceToQuery,ToolCallCorrectness`)
- `output_format` (optional) — `"table"` or `"json"`

**Regression-focused cert:** If the user asks to include regression follow-ups, first
`mcp_mlflow_search_traces` with tags/filter for `regression=true` (or dataset tag), evaluate
those traces preferentially, and state the sample composition in the report.

**Link traces to evaluation run:** After evaluation, use `mcp_mlflow_link_traces_to_run` to associate the evaluated trace IDs with the evaluation run for traceability.

**`mcp_mlflow_link_traces_to_run` parameters:**
- `run_id` (string, required) — the evaluation run ID
- `trace_ids` (array of strings, required) — trace IDs to link (max 100)

### Step 6: Record qualification verdict

Record the qualification result as a run with structured tags:

1. `mcp_mlflow_create_run` — create a qualification run in the experiment with:
   - `run_name`: `qualification-<date>`
   - `tags`: `profile=<scorer_profile>`, `verdict=QUALIFIED|NOT_QUALIFIED|NEEDS_REVIEW`
   - `status`: `FINISHED`

> **Note:** Writing qualification to LoggedModel tags (`search_logged_models`, `set_logged_model_tags`)
> requires the Gateway MCP (M2). Until then, qualification verdicts are recorded as evaluation runs.

### Step 7: Generate Quality Qualification Report

Aggregate MCP JSON only (optional code execution on returned data). Never `import mlflow`.

## Scoring rules

| Signal | How to report | Default threshold |
|--------|---------------|-------------------|
| Built-in GenAI scorer | Pass rate = (# yes or positive) / (# scored) | **≥ 80%** PASS |
| Trace status ERROR | Error rate on sample | **< 5%** for QUALIFIED |
| Scorer `feedback.error` | Scorer failure — exclude from pass rate; call out separately | — |

`state: OK` / `STATUS_CODE_OK` means the run completed — **not** that the answer is correct.

## Output Format

```
# Quality Qualification Report
## Agent: [name] | Experiment: [id]
## Date: [timestamp] | Evaluator: Agent Lens

### Profile: [RAG/Tool-Calling/Chat]

### Scores (pass rates — GenAI yes/no scorers)
| Dimension | Pass rate | Rating | Threshold |
|-----------|-----------|--------|-----------|
| RelevanceToQuery | XX% | PASS/FAIL | >= 80% |
| RetrievalGroundedness | XX% or N/A | PASS/FAIL/SKIPPED | >= 80% |
| ToolCallCorrectness | XX% | PASS/FAIL | >= 80% |

### Qualification verdict (chat — not a CI pipeline block)
**[QUALIFIED / NOT QUALIFIED / NEEDS REVIEW]**

Rules of thumb:
- QUALIFIED: all required scorers PASS and error rate < 5%
- NOT QUALIFIED: any required scorer FAIL or error rate >= 5%
- NEEDS REVIEW: missing retriever spans, scorer errors, or insufficient sample

### Evidence
- Traces evaluated: N (dry-run + full)
- Error rate: X%
- Avg latency: Xms
- Regression-tagged traces included: Y/N

### Findings (if NOT QUALIFIED / NEEDS REVIEW)
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
