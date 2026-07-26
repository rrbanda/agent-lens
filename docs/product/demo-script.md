# Demo Script

Step-by-step demonstration of Agent Lens with **upstream official MLflow MCP**.

## Preflight (do not skip)

Complete **before** opening the dashboard:

- [ ] `make status` shows official MCP pod(s) and Agent Lens Ready
- [ ] Secrets exist: `agent-lens-llm-key` and `agent-lens-auth` (see `make secret`)
- [ ] Target agent has traces — [first-trace.md](first-trace.md) (≥5 recommended)
- [ ] You understand [limitations.md](limitations.md) (qualify ≠ CI gate; tags ≠ dataset API)

```bash
make status
MCP_URL=http://mlflow-mcp.redhat-ods-applications.svc.cluster.local:8080/mcp \
  ./scripts/check_mcp_contract.sh || true
```

## Demo flow

### Act 1: Orientation (2 min)

1. Open the Agent Lens dashboard Route
2. Login with credentials from `agent-lens-auth` (`dashboard-password`)
3. Start a new chat

**Say:** "Agent Lens is a conversational qualification layer on official MLflow MCP —
not a custom scoring sidecar."

### Act 2: Discovery (3 min)

**Prompt:**
```
What experiments are being tracked?
```

**Expected:** `mcp_mlflow_search_experiments` → formatted table.

**Prompt:**
```
Show me the last 20 traces for <experiment-name>
```

**Expected:** trace-explorer → `mcp_mlflow_search_traces` table (status, latency, tokens).

### Act 3: Evaluation / qualify (4 min)

**Prompt:**
```
Evaluate the outreach agent using the tool-calling profile
```

**Expected:** dry-run then full `mcp_mlflow_evaluate_traces` → Quality Qualification
Report with **pass rates** (yes/no scorers, ≥80% threshold) — not `/5` scores.

**Prompt:**
```
Can this agent be deployed?
```

**Expected:** Skill-side **qualification verdict** from scores vs thresholds.
Clarify for the audience: this does **not** block a pipeline yet
([issue #18](https://github.com/rrbanda/agent-lens/issues/18)).

### Act 4: Human review (3 min)

**Prompt:**
```
Show me traces that need review
```

**Expected:** `mcp_mlflow_search_traces` with error/recent heuristics — not a dedicated queue API.

**Prompt:**
```
That first trace looks problematic — annotate it as incorrect tool selection with a score of 2
```

**Expected:** `mcp_mlflow_log_trace_feedback`.

### Act 5: Regression follow-up (3 min)

**Prompt:**
```
Log a regression follow-up for that failing trace
```

**Expected:** `mcp_mlflow_log_trace_expectation` + `mcp_mlflow_set_trace_tag`
(`regression=true`). Say aloud: this is **not** creating an MLflow Evaluation Dataset.

### Act 6: Fleet overview (2 min)

**Prompt:**
```
Give me a quality dashboard across all agents
```

**Expected:** `search_experiments` + capped per-experiment `search_traces` / `list_runs`
(**not** `import mlflow` in the sandbox). HEALTHY/WARNING/CRITICAL/INACTIVE summary.

**Verify:**
1. Tool calls are `mcp_mlflow_*` only
2. Zero traces → INACTIVE, no DB connection errors
3. With seeded traces → non-INACTIVE rows

## Key points

1. Evaluation on production traces via official MCP
2. Honest AgentOps: qualify in chat today; CI gate on the roadmap
3. Skills encode methodology; MCP owns MLflow access
4. Empty fleet is an instrumentation problem, not an Agent Lens outage

## Troubleshooting

| Issue | Quick fix |
|-------|-----------|
| No experiments | [operator-mcp.md](operator-mcp.md) + MLflow workspace |
| Connection refused | `oc get pods -l app=mlflow-mcp -n redhat-ods-applications` |
| All INACTIVE | [first-trace.md](first-trace.md) |
| Sandbox `import mlflow` | Sync soul/skills ConfigMaps from this repo |
| Slow responses | Cap fleet scan; Gemini rate limits — retry |

## Optional API call

```bash
curl -X POST "https://<agent-lens-route>/api/v1/chat" \
  -H "Authorization: Bearer $API_SERVER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Evaluate experiment 1 with RAG profile"}'
```

Use the API key from secret `agent-lens-auth` / `api-server-key`.
