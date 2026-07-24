# Demo Script

A step-by-step demonstration of Agent Lens capabilities.

## Prerequisites

- Agent Lens deployed and accessible via Route
- At least one agent instrumented with `usercustomize.py` and generating traces
- (Optional) At least one evaluation run completed via `eval_agent.py`

## Demo Flow

### Act 1: Orientation (2 min)

**Goal**: Show what Agent Lens is and how it connects to the ecosystem.

1. Open the Agent Lens dashboard in a browser
2. Login with `admin` / `openshift`
3. Start a new chat session

**Say**: "Agent Lens is a conversational observability tool. Instead of clicking
through dashboards, you ask questions in plain English."

### Act 2: Discovery (3 min)

**Prompt**:
```
What experiments are being tracked?
```

**Expected**: Agent calls `mcp_mlflow_list_experiments` and returns a formatted table
of all experiments with IDs, names, and status.

**Prompt**:
```
Show me the last 20 traces for <experiment-name>
```

**Expected**: Agent uses the trace-explorer skill. Returns a table with timestamp,
status, latency, and token usage for each trace.

### Act 3: Diagnostics (3 min)

**Prompt**:
```
Are there any errors in the last hour?
```

**Expected**: Agent searches for traces with `status = 'ERROR'`, counts them,
computes error rate, and flags if it's above normal.

**Prompt** (if errors found):
```
Diagnose the most recent failure
```

**Expected**: Agent uses diagnose-failure skill. Pulls the failing trace,
identifies the step that failed, maps it to the failure taxonomy, and
suggests remediation.

### Act 4: Quality Assessment (3 min)

**Prompt**:
```
What's the quality score from the last evaluation?
```

**Expected**: Agent uses eval-report skill. Searches for eval runs, pulls
metrics (relevance, faithfulness, correctness), and formats a quality report
with ratings and trends.

**Prompt**:
```
Compare the last two evaluation runs
```

**Expected**: Agent uses compare-agents skill. Finds the two most recent
eval runs, calls `compare_runs`, presents a delta table showing which
improved and which regressed.

### Act 5: Fleet Overview (2 min)

**Prompt**:
```
Give me a quality dashboard across all agents
```

**Expected**: Agent uses quality-dashboard skill with code execution (aggregates
data across multiple experiments). Returns a fleet-wide health summary with
status indicators and alerts.

## Key Points to Highlight

1. **No context switching** — engineers stay in one interface, ask natural language
2. **Hybrid intelligence** — native MCP for speed, code execution for depth
3. **Skill-based** — each analytical pattern is a documented, extensible skill
4. **Zero-code instrumentation** — adding observability to a new agent is one file copy
5. **Production architecture** — RBAC, secrets management, persistent state, HTTPS

## Troubleshooting During Demo

| Issue | Quick Fix |
|-------|-----------|
| "No experiments found" | Check MLFLOW_WORKSPACE in MCP server config |
| "Connection refused" | Verify MCP server pod is running: `oc get pods -l app=mlflow-mcp-server` |
| Agent responds slowly | Gemini rate limits — wait 30s and retry |
| "No traces found" | Ensure target agent has made LLM calls recently |
| Dashboard won't load | Check route: `oc get route agent-lens` |

## Advanced Demo (Optional)

### Live Instrumentation

1. Show a target agent without instrumentation
2. Add `usercustomize.py` to its environment
3. Make a few requests to the target agent
4. Switch to Agent Lens: "Show the last 5 traces for <new-agent>"
5. See traces appear in real-time

### Evaluation Loop

1. Run `make eval` against the target agent
2. Switch to Agent Lens: "What was the quality score from the eval I just ran?"
3. Show the agent finding and reporting the fresh results
