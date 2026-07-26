---
name: "eval-loop"
description: "Run a full Evaluation-Driven Development cycle: baseline eval, failure diagnosis, re-evaluation after fixes, and comparison. Use when asked to improve an agent iteratively, compare before/after, or run an EDD loop."
---

# Evaluation-Driven Development Loop

Orchestrate the full EDD (Evaluation-Driven Development) cycle in a single conversation
via **upstream official MLflow MCP**.
Inspired by [MLflow Cookbook: Evaluation-Driven Development](https://mlflow.org/cookbook/eval-driven-development/).

The loop: **Baseline → Diagnose → Fix → Re-evaluate → Compare**.

## When to Use

- "Start an eval-driven development cycle on the support agent"
- "I fixed the prompt — re-run and compare to baseline"
- "Show me what failed and why, then help me improve"
- "Run a before/after comparison on the RAG agent"
- "Help me iterate on agent quality"

## Strategy

### Phase 1: Baseline Evaluation

#### Step 1.1: Identify Agent and Scorers

1. `mcp_mlflow_search_experiments` — find the target experiment
2. Ask user what dimensions matter, or suggest based on agent type:
   - RAG: `RelevanceToQuery`, `RetrievalGroundedness`
   - Tool-calling: `ToolCallCorrectness`, `ToolCallEfficiency`, `RelevanceToQuery`
   - Chat: `RelevanceToQuery`, Guidelines
3. `mcp_mlflow_list_scorers` — confirm scorers are available

#### Step 1.2: Run Baseline

1. `mcp_mlflow_search_traces` — get recent traces (50 for baseline)
2. `mcp_mlflow_evaluate_traces` — run with selected scorers
3. `mcp_mlflow_create_run` — record baseline:
   - `run_name`: `edd-baseline-<date>`
   - `tags`: `edd-phase=baseline`, `edd-cycle=<cycle_id>`

#### Step 1.3: Record Baseline Metrics

Present pass rates per scorer. This is the number to beat.

```
## EDD Baseline
| Scorer | Pass Rate | Threshold | Status |
|--------|-----------|-----------|--------|
| RelevanceToQuery | XX% | >= 80% | PASS/FAIL |
| [other scorer] | XX% | >= 80% | PASS/FAIL |
| Error Rate | X% | < 5% | PASS/FAIL |
```

---

### Phase 2: Diagnose Failures

#### Step 2.1: Identify Failed Traces

From the evaluation results, find traces that scored FAIL on any dimension.

#### Step 2.2: Drill Into Failures

For top 3-5 failures:
1. `mcp_mlflow_get_trace` — fetch full trace with spans
2. Extract the scorer rationale explaining why it failed
3. Group failures by pattern (common root cause)

#### Step 2.3: Present Failure Analysis

```
## Failure Patterns

### Pattern 1: [Description] (N traces)
- Root cause: [what's going wrong]
- Example trace: [trace_id] — [brief summary]
- Scorer rationale: "[rationale from scorer]"

### Pattern 2: [Description] (N traces)
- Root cause: [what's going wrong]
- Example trace: [trace_id] — [brief summary]
- Scorer rationale: "[rationale from scorer]"

### Recommended Fixes
1. [Most impactful fix — addresses Pattern 1]
2. [Second fix — addresses Pattern 2]
3. [Optional: systemic improvement]
```

#### Step 2.4: Annotate Ground Truth

For key failure traces, log what the correct output should be:
1. `mcp_mlflow_log_trace_expectation` — record expected output
2. `mcp_mlflow_set_trace_tag` — tag `edd-baseline=true`

---

### Phase 3: Wait for Fix

Tell the user:
- What to fix (based on failure analysis)
- What to change (prompt, retrieval config, tool definitions, etc.)
- When to come back ("after deploying the fix, ask me to re-evaluate")

**Pause here.** The user must fix their agent and generate new traces before Phase 4.

When the user returns saying they fixed it, proceed to Phase 4.

---

### Phase 4: Re-evaluate

#### Step 4.1: Get New Traces

1. `mcp_mlflow_search_traces` — get traces generated **after** the fix
   - Use time filter or rely on recent traces
   - Same sample size as baseline (50)

#### Step 4.2: Run Same Evaluation

1. `mcp_mlflow_evaluate_traces` — same scorers as baseline
2. `mcp_mlflow_create_run` — record improved:
   - `run_name`: `edd-improved-<date>`
   - `tags`: `edd-phase=improved`, `edd-cycle=<cycle_id>`

---

### Phase 5: Compare

#### Step 5.1: Retrieve Both Runs

1. `mcp_mlflow_list_runs` — find baseline and improved runs by `edd-cycle` tag
2. `mcp_mlflow_describe_run` — get metrics for both

#### Step 5.2: Generate Comparison Report

## Output Format

```
# EDD Cycle Report
## Agent: [name] | Experiment: [id]
## Cycle: [cycle_id] | Date: [timestamp]

### Improvement Summary
| Scorer | Baseline | After Fix | Delta | Verdict |
|--------|----------|-----------|-------|---------|
| RelevanceToQuery | XX% | XX% | +X% | IMPROVED/SAME/REGRESSED |
| [other scorer] | XX% | XX% | +X% | IMPROVED/SAME/REGRESSED |
| Error Rate | X% | X% | -X% | IMPROVED/SAME/REGRESSED |

### Overall Verdict
**[IMPROVED / NO CHANGE / REGRESSED]**

Rules:
- IMPROVED: At least one scorer improved without any regressing
- NO CHANGE: All deltas within +/- 2%
- REGRESSED: Any scorer dropped by more than 5%

### What Changed
- Fix applied: [user's description of what they changed]
- Traces evaluated: N baseline, N improved

### Failure Patterns Resolved
- [Pattern 1]: [resolved/partially resolved/unresolved]
- [Pattern 2]: [resolved/partially resolved/unresolved]

### Remaining Issues
[If any scorer still fails threshold, list what remains]

### Next Steps
- [ ] [If IMPROVED] Consider qualification via `evaluate-agent`
- [ ] [If NO CHANGE] Try a different fix approach
- [ ] [If REGRESSED] Revert and investigate what went wrong
- [ ] Run another EDD cycle for remaining issues
```

## Multi-Cycle Support

If the user wants to iterate further:
- Increment cycle_id
- The "improved" run from this cycle becomes the "baseline" for the next
- Track cumulative improvement across cycles

## Anti-patterns

- Never skip the baseline — always have a "before" to compare against
- Never compare traces from different time periods without acknowledging data drift
- Never claim improvement without running the same scorers on both sets
- Never run Phase 4 before the user confirms they made changes
- Never evaluate fewer than 20 traces per phase for meaningful comparison
- Never `import mlflow` in the sandbox — all evaluation via MCP
