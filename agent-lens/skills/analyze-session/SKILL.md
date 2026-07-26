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

### Conversational Quality Evaluation

When the user asks to *evaluate* session quality (not just debug), use MLflow's built-in
conversational scorers. These were designed specifically for multi-turn evaluation
(see [MLflow Cookbook: Evaluating a Multi-Turn Conversational Agent](https://mlflow.org/cookbook/multi-turn-agent/)).

6. **Run conversational scorers:** Call `mcp_mlflow_evaluate_traces` with the session's trace IDs
   and these built-in conversational scorers (verify availability via `mcp_mlflow_list_scorers` first):

   | Scorer | What It Checks | Returns |
   |--------|---------------|---------|
   | `ConversationCompleteness` | Did the agent address ALL user requests by the end? | `"yes"` / `"no"` |
   | `ConversationalGuidelines` | Did the agent follow specified rules across the full conversation? | `"yes"` / `"no"` |
   | `UserFrustration` | Did the user show frustration, and was it resolved? | `"none"` / `"resolved"` / `"unresolved"` |
   | `KnowledgeRetention` | Did the agent remember facts from earlier turns? | `"yes"` / `"no"` |
   | `ConversationalSafety` | Did the agent maintain safety across the conversation? | `"yes"` / `"no"` |
   | `ConversationalRoleAdherence` | Did the agent stay in its assigned role? | `"yes"` / `"no"` |

   **Default scorer set for session eval:** `ConversationCompleteness`, `UserFrustration`, `ConversationalGuidelines`.
   Only add `ConversationalGuidelines` when the user provides specific rules to check against.

7. **Interpret results using the cookbook interpretation pattern:**

   | Completeness | Guidelines | Frustration | Meaning |
   |-------------|-----------|-------------|---------|
   | yes | yes | none | Clean conversation — all questions answered |
   | yes | no | unresolved | Agent violated rules; user frustrated and unresolved |
   | no | yes | none | Agent missed some requests but followed rules |
   | no | no | unresolved | Broken conversation — needs immediate attention |

8. **Quality degradation check:** Compare per-turn `RelevanceToQuery` scores across early turns
   (1-3) vs late turns (N-2 to N). If late turns score lower, flag as "quality degradation."

9. **Session-level verdict:**
   - GOOD: Completeness=yes AND Frustration=none
   - NEEDS ATTENTION: Completeness=no OR Frustration=resolved
   - CRITICAL: Frustration=unresolved OR multiple guideline violations

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
- Conversational evaluation uses MLflow's built-in conversational scorers — do NOT create custom judges for
  completeness, frustration, or role adherence. These are built in.
- Only run conversational scorers when user asks to evaluate quality, not for basic debugging.
- `ConversationalGuidelines` requires explicit guideline strings — ask the user or derive from agent's system prompt.
