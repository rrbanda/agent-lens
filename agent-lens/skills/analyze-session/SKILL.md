---
name: "analyze-session"
description: "Analyze a multi-turn chat session (linked traces) to find where the conversation went wrong. Use when asked to debug a chat, review session history, or analyze patterns across turns."
---

# Analyze Session

Multi-turn session forensics via **upstream official MLflow MCP**.
Adapted from [mlflow/skills analyze-mlflow-chat-session](https://github.com/mlflow/skills/tree/main/analyze-mlflow-chat-session).
Enhanced with conversational evaluation patterns from [MLflow Cookbook: Evaluating a Multi-Turn Conversational Agent](https://mlflow.org/cookbook/evaluating-multi-turn-conversational-agent).

## When to Use

- "Debug this chat session"
- "Where did this conversation go wrong?"
- "Review session history"
- "Analyze chat for user X / session Y"
- "Evaluate conversation quality for this session"
- "Does quality degrade across turns?"

## Strategy (MCP-first)

Sessions are traces sharing metadata key `mlflow.trace.session` (dots in the key — follow MCP filter schema).

1. If the user gives a **trace id**, `mcp_mlflow_get_trace` and read session id from metadata.
2. `mcp_mlflow_search_traces` filtered by that session id; order by time ascending when the API allows.
3. For schema discovery: `mcp_mlflow_get_trace` on the **first** turn only; find root span I/O attributes.
4. Summarize each turn (user intent → agent action → outcome). Fetch full detail only for failing / suspicious turns.
5. Assessments:
   - Session-level assessments often live on the **first** trace
   - Exclude assessments with `feedback.error` (scorer failure ≠ agent failure)
   - Always surface **rationale**

### Optional: Conversational Quality Evaluation

When the user asks to *evaluate* session quality (not just debug), add these steps:

6. **Turn-by-turn evaluation:** Run `mcp_mlflow_evaluate_traces` on the session's traces with `RelevanceToQuery` to get per-turn quality scores.

7. **Quality degradation check:** Compare pass rates across early turns (1-3) vs late turns (N-2 to N). If late turns score lower, flag as "quality degradation" — a common issue in long conversations where context windows fill up.

8. **Conversational coherence:** If no custom conversational judge exists, suggest creating one via `create-judge`:
   - "Does the agent maintain context from previous turns?"
   - "Does the agent avoid repeating information already provided?"
   - "Does the agent correctly reference entities introduced in earlier turns?"

9. **Session-level verdict:** Aggregate per-turn scores into a session quality summary:
   - ALL TURNS PASS: Session quality GOOD
   - Late turns degrade: CONTEXT DEGRADATION
   - Scattered failures: INCONSISTENT
   - Multiple consecutive failures: BREAKDOWN at turn N

Never `import mlflow` in the sandbox.

## Output Format

```
## Session Analysis: [session_id]

### Overview
| Field | Value |
|-------|-------|
| Turns (traces) | N |
| Experiment | [id/name] |
| Span of time | ... |
| Session Quality | GOOD / CONTEXT DEGRADATION / INCONSISTENT / BREAKDOWN |

### Turn Timeline
| # | Trace | State | Latency | Quality | Issue? |
|---|-------|-------|---------|---------|--------|
| 1 | ... | OK | ... | PASS | — |
| 2 | ... | OK | ... | PASS | — |
| 3 | ... | OK | ... | FAIL | Tool X failed |
| 4 | ... | ERROR | ... | FAIL | Context lost |

### Quality Across Turns (if evaluation was run)
| Segment | Turns | Pass Rate | Observation |
|---------|-------|-----------|-------------|
| Early (1-3) | 3 | 100% | Baseline quality |
| Middle (4-6) | 3 | 67% | Slight degradation |
| Late (7+) | N | XX% | [stable/degrading/collapsed] |

### Where it went wrong
1. [Turn N — evidence from spans/assessments]
2. [Pattern: quality degraded after turn X due to ...]

### Recommended actions
- Annotate turn N (`review-trace`)
- Regression follow-up on failing turn (`create-regression`)
- Re-evaluate agent after fix (`evaluate-agent`)
- [If degradation] Create a conversational coherence judge (`create-judge`)
- [If context issues] Investigate context window management in the agent
```

## Notes

- If session metadata is missing, say so and fall back to single-trace `review-trace`.
- Do not fetch full JSON for every turn when a search listing is enough.
- Conversational evaluation is **optional** — only run when user asks to evaluate quality, not for basic debugging.
- If no conversational scorer exists, suggest `create-judge` with coherence criteria.
