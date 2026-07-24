# Demo Script

A step-by-step demonstration of Agent Lens v2 capabilities.

## Prerequisites

- Agent Lens deployed and accessible via Route
- At least one agent instrumented with MLflow autologging and generating traces
- Dashboard password set via `agent-lens-auth` secret

## Demo Flow

### Act 1: Orientation (2 min)

**Goal**: Show what Agent Lens is and how it connects to the ecosystem.

1. Open the Agent Lens dashboard in a browser
2. Login with the credentials from the `agent-lens-auth` secret
3. Start a new chat session

**Say**: "Agent Lens is a conversational evaluation platform. Instead of clicking
through dashboards, you ask questions in plain English — and it runs MLflow's
evaluation APIs behind the scenes."

### Act 2: Discovery (3 min)

**Prompt**:
```
What experiments are being tracked?
```

**Expected**: Agent calls `mcp_agent-lens_list_experiments` and returns a formatted
table of all experiments with IDs, names, and status.

**Prompt**:
```
Show me the last 20 traces for <experiment-name>
```

**Expected**: Agent uses the trace-explorer skill. Returns a table with timestamp,
status, latency, and token usage for each trace.

### Act 3: Evaluation (4 min)

**Prompt**:
```
Evaluate the outreach agent using the tool-calling profile
```

**Expected**: Agent uses the evaluate-agent skill. Calls `mcp_agent-lens_run_evaluation`
with ToolCallCorrectness + ToolCallEfficiency + RelevanceToQuery scorers. Returns a
Quality Certification Report with per-dimension scores and a PASS/FAIL verdict.

**Prompt**:
```
Can this agent be deployed?
```

**Expected**: Agent calls `mcp_agent-lens_check_quality_gate` with the experiment ID.
Returns PASS/FAIL with specific metrics that drove the decision.

### Act 4: Human Review (3 min)

**Prompt**:
```
Show me traces that need review
```

**Expected**: Agent calls `mcp_agent-lens_get_review_queue`. Returns traces ordered by
priority — those without assessments or with low automated scores.

**Prompt**:
```
That first trace looks problematic — annotate it as "incorrect tool selection"
with a score of 2
```

**Expected**: Agent calls `mcp_agent-lens_annotate_trace` to persist the feedback.
Confirms the annotation was logged in MLflow.

### Act 5: Closing the Loop (3 min)

**Prompt**:
```
Add that failing trace to the regression dataset
```

**Expected**: Agent uses create-regression skill. Calls `mcp_agent-lens_create_test_case`
to convert the trace into an evaluation dataset entry. Next evaluation run will
automatically catch this case.

### Act 6: Fleet Overview (2 min)

**Prompt**:
```
Give me a quality dashboard across all agents
```

**Expected**: Agent uses quality-dashboard skill. Aggregates data across
multiple experiments and returns a fleet-wide health summary with HEALTHY/WARNING/CRITICAL
status indicators and alerts.

## Key Points to Highlight

1. **Evaluation, not just observability** — Agent Lens scores agent quality, not just logs
2. **AgentOps loop** — observe → evaluate → annotate → gate → improve, all conversational
3. **MLflow-native** — uses `mlflow.genai.evaluate()` directly, not custom scoring
4. **Skill-based** — each analytical pattern is a documented, extensible skill
5. **Production-grade** — TLS, secrets, NetworkPolicies, security contexts, health probes

## Troubleshooting During Demo

| Issue | Quick Fix |
|-------|-----------|
| "No experiments found" | Check MLflow tracking URI in MCP server ConfigMap |
| "Connection refused" | Verify MCP server pod is running: `oc get pods -l app=mlflow-mcp-server` |
| Agent responds slowly | Gemini rate limits — wait 30s and retry |
| "No traces found" | Ensure target agent has made LLM calls recently |
| Dashboard won't load | Check route: `oc get route agent-lens` |
| "Operation timed out" | MCP server has 30s default timeout; evaluations get 120s |

## Advanced Demo (Optional)

### Run Evaluation from CLI

```bash
curl -X POST "https://<agent-lens-route>/api/v1/chat" \
  -H "Authorization: Bearer $API_SERVER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Evaluate experiment 1 with RAG profile"}'
```

### Custom Scorer via Guidelines

```
You: "Evaluate the agent with custom guidelines: responses must never suggest
     contacting a competitor, must always include a CTA, and should be under 200 words"
```

Agent Lens will use the `Guidelines` scorer with your custom rules.
