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

Confirm availability with `mcp_mlflow_list_scorers` (pass `builtin: "true"` for built-in scorers,
or `experiment_id` for custom registered scorers). **Both parameters are optional but at least one is required.**

The following scorers are confirmed available from the MLflow cookbooks. Use `mcp_mlflow_list_scorers`
to verify exact names on the target server.

**RAG Agent Profile** (from [End-to-End RAG Evaluation](https://mlflow.org/cookbook/rag-evaluation/) cookbook):
- `RelevanceToQuery` — Is the answer relevant to the question?
- `RetrievalGroundedness` — Is the answer grounded in retrieved context (not hallucinated)?
- `RetrievalSufficiency` — Did the retriever fetch enough relevant context to answer?
- `Correctness` — Does the response match expected facts?
  - **Prerequisite:** `RetrievalGroundedness` and `RetrievalSufficiency` require traces with `RETRIEVER` spans.

**Tool-Calling Agent Profile** (from [LangGraph Agent](https://mlflow.org/cookbook/langgraph-agent/) and [OpenAI Agents](https://mlflow.org/cookbook/openai-agents/) cookbooks):
- `ToolCallCorrectness` — Are tool calls and arguments correct? Uses fuzzy matching.
- `Correctness` — Does the final answer contain expected facts?
- `RelevanceToQuery` — Does the final answer address the user?

**Chat Agent Profile** (from [EDD](https://mlflow.org/cookbook/eval-driven-development/) cookbook):
- `RelevanceToQuery` — Addresses the user's intent?
- `Correctness` — Matches expected response?
- `Guidelines` — Custom rule compliance (user provides rules)

**Multi-Turn Profile** (from [Multi-Turn Conversational Agent](https://mlflow.org/cookbook/multi-turn-agent/) cookbook):
- `ConversationCompleteness` — Did agent address ALL user requests by session end?
- `ConversationalGuidelines` — Did agent follow rules across full conversation?
- `UserFrustration` — Was user frustration detected and resolved?

**Safety Profile** (from [Red-Teaming](https://mlflow.org/cookbook/red-teaming/) cookbook):
- `Safety` — Detects harmful/toxic content
- Custom `Guidelines` judges for `no_prompt_leak`, `no_pii`, `stays_on_topic`

**Custom Profile** — Ask the user what dimensions matter most (`Guidelines` / registered scorers).

**Registering custom scorers:** Use `mcp_mlflow_register_llm_judge_scorer` to register a custom LLM judge scorer with specific instructions for domain-specific evaluation. Verify availability with `mcp_mlflow_list_scorers` before using in evaluation.

**`mcp_mlflow_register_llm_judge_scorer` parameters (from live MCP schema):**
- `name` (string, required) — unique scorer name
- `instructions` (string, required) — judging instructions; must contain template variables like `{{ inputs }}`, `{{ outputs }}`
- `experiment_id` (string, required) — experiment to register the scorer under
- `model` (string, optional) — LLM model URI (e.g. `openai:/gpt-4o-mini`). Defaults to OpenAI.
- `base_url` (string, optional) — custom LLM endpoint URL (for non-OpenAI models)
- `extra_headers` (string, optional) — additional HTTP headers for the LLM endpoint
- `description` (string, optional) — human-readable description of the scorer

**Important:** If no `OPENAI_API_KEY` is set in the MLflow MCP environment, you must specify `model` and `base_url` pointing to an available LLM endpoint, otherwise judge registration succeeds but evaluation will fail.

### Step 4: Dry run (required before full cert)

First `mcp_mlflow_search_traces` to get trace IDs, then evaluate a **small** sample first (3–5 trace IDs).
If scorers error, tools are broken, or all traces empty — stop and report; do not run 50–200.

### Step 5: Full evaluation

1. `mcp_mlflow_search_traces` to collect trace IDs:
   - Quick check: 50 traces
   - Qualification: 200 traces
2. `mcp_mlflow_evaluate_traces` with the collected trace IDs and chosen scorers.

**`mcp_mlflow_evaluate_traces` parameters (from live MCP schema):**
- `experiment_id` (string, required) — target experiment
- `trace_ids` (string, required) — comma-separated trace IDs (e.g. `tr-abc123,tr-def456`)
- `scorers` (string, required) — comma-separated scorer names (e.g. `RelevanceToQuery,ToolCallCorrectness`)
- `output_format` (string, optional) — `"table"` (default) or `"json"`

**There is no `max_traces` parameter.** You control sample size by how many trace IDs you pass.

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
   - `tags`: `["profile=<scorer_profile>", "verdict=QUALIFIED|NOT_QUALIFIED|NEEDS_REVIEW"]` (array of `key=value` strings)
   - `status`: `FINISHED`

> **Note:** Writing qualification to LoggedModel tags (`search_logged_models`, `set_logged_model_tags`)
> `search_logged_models` is not yet in the MLflow MCP tool set. Until then, qualification verdicts are recorded as evaluation runs.

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
