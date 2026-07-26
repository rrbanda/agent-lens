---
name: "agent-registry"
description: "Fleet inventory of all agents with qualification status, configuration, and lifecycle metadata. Use when asked about agent inventory, fleet overview, registration, or which agents are qualified."
---

# Agent Registry

Centralized fleet inventory backed by MLflow LoggedModel, providing qualification status at a glance.

## When to Use

- "Show me all registered agents"
- "What agents are qualified for production?"
- "Register agent X"
- "What's the status of our agent fleet?"
- "Which agents need re-qualification?"

## Strategy

### Step 1: List registered agents

`mcp_mlflow_search_logged_models` — returns all LoggedModels tracked in MLflow.

Filter by Agent Lens tags:
- `agentlens.managed=true` — agents under Agent Lens governance
- `agentlens.qualification.status` — current qualification verdict

### Step 2: Enrich with details (if specific agent)

For a specific agent:
1. `mcp_mlflow_get_logged_model` — full metadata, tags, parameters
2. Read `agentlens.qualification.*` tags for qualification state
3. `mcp_mlflow_search_traces` — recent trace activity

### Step 3: Register a new agent

When asked to register a new agent:

1. `mcp_mlflow_create_logged_model` or `mcp_mlflow_create_external_model` — create the LoggedModel entry
2. `mcp_mlflow_set_logged_model_tags` — set initial tags:
   - `agentlens.managed=true`
   - `agentlens.qualification.status=PENDING`
   - `agentlens.agent_type` = RAG / tool-calling / chat
   - `agentlens.owner` = team or individual
3. `mcp_mlflow_log_logged_model_params` — store agent configuration parameters

### Step 4: Present fleet view

## Output Format

```
## Agent Registry
### Fleet: [N] agents | Qualified: [X] | Pending: [Y] | Not Qualified: [Z]

| Agent | Type | Status | Last Qualified | Pass Rate | Owner |
|-------|------|--------|---------------|-----------|-------|
| outreach-agent | RAG | QUALIFIED | 2026-07-15 | 92% | team-alpha |
| support-bot | Chat | NOT QUALIFIED | 2026-07-10 | 68% | team-beta |
| data-analyst | Tool-Calling | PENDING | — | — | team-gamma |

### Agents Needing Attention
- **support-bot**: Failed qualification on 2026-07-10 (RelevanceToQuery 68%)
- **data-analyst**: Never evaluated — registered but no qualification run
```

## Lifecycle States

| State | Meaning | Next action |
|-------|---------|-------------|
| PENDING | Registered, never evaluated | Run `evaluate-agent` |
| QUALIFIED | Passed qualification | Re-qualify before TTL expiry |
| NOT_QUALIFIED | Failed qualification | Fix issues, re-evaluate |
| NEEDS_REVIEW | Inconclusive evaluation | Manual review required |
| RETIRED | Decommissioned | No action |

## Constraints

- All registry data lives in MLflow LoggedModel — no separate database
- Use `agentlens.*` tag namespace to avoid conflicts with other tools
- Cap fleet scans at 50 agents per query
- Never `import mlflow` in the sandbox
