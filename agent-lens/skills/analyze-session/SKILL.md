---
name: "analyze-session"
description: "Analyze a multi-turn chat session (linked traces) to find where the conversation went wrong. Use when asked to debug a chat, review session history, or analyze patterns across turns."
---

# Analyze Session

Multi-turn session forensics via **upstream official MLflow MCP**.
Adapted from [mlflow/skills analyze-mlflow-chat-session](https://github.com/mlflow/skills/tree/main/analyze-mlflow-chat-session).

## When to Use

- "Debug this chat session"
- "Where did this conversation go wrong?"
- "Review session history"
- "Analyze chat for user X / session Y"

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

### Turn Timeline
| # | Trace | State | Latency | Issue? |
|---|-------|-------|---------|--------|
| 1 | ... | OK | ... | — |
| 2 | ... | OK | ... | Tool X failed |

### Where it went wrong
1. [Turn N — evidence from spans/assessments]

### Recommended actions
- Annotate turn N (`review-trace`)
- Regression follow-up on failing turn (`create-regression`)
- Re-evaluate agent after fix (`evaluate-agent`)
```

## Notes

- If session metadata is missing, say so and fall back to single-trace `review-trace`.
- Do not fetch full JSON for every turn when a search listing is enough.
