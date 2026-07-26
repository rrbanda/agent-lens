---
name: "executive-summary"
description: "Generate a non-technical, one-paragraph fleet health summary for leadership. Use when asked for a high-level overview, board-ready summary, or executive briefing on agent fleet status."
---

# Executive Summary

Non-technical fleet health summary for CTO, Director, and VP-level stakeholders.

## When to Use

- "Give me a quick summary for leadership"
- "How's our agent fleet doing?"
- "Board-ready summary of agent quality"
- "Executive briefing on agent status"
- "TL;DR of our agent portfolio"

## Strategy

### Step 1: Gather fleet-wide data

1. `mcp_mlflow_search_logged_models` — get all agents with `agentlens.managed=true`
2. Read `agentlens.qualification.*` tags for status distribution
3. `mcp_mlflow_search_experiments` — get experiment metadata for active agents

### Step 2: Compute fleet health indicators

Using code execution on returned MCP data:

- **Fleet size**: total registered agents
- **Qualification distribution**: QUALIFIED / NOT QUALIFIED / PENDING / NEEDS REVIEW
- **Coverage**: % of agents that have been evaluated at least once
- **Risk agents**: agents that are NOT QUALIFIED or overdue for re-qualification
- **Trend**: improving, stable, or declining (compare current vs. previous period if data available)

### Step 3: Generate executive narrative

Write a **single paragraph** that a non-technical executive can read in 30 seconds. Follow with a compact table only if it adds clarity.

## Output Format

```
## Agent Fleet Health — Executive Summary
### As of [date]

**[One paragraph, 3-5 sentences]** — e.g., "Your organization manages 12 AI agents
across 4 teams. 8 are qualified for production (67%), 2 failed their last evaluation
and need attention, and 2 have never been evaluated. The outreach-agent and
support-bot require immediate remediation — both failed on answer relevance.
Overall fleet health is stable compared to last month."

### At a Glance
| Indicator | Value |
|-----------|-------|
| Total agents | 12 |
| Production-qualified | 8 (67%) |
| Needs remediation | 2 |
| Never evaluated | 2 |
| Fleet health trend | → Stable |

### Action Items
1. **support-bot** — failed RelevanceToQuery (68%), team-beta owns
2. **data-analyst** — never evaluated, recommend initial qualification
```

## Tone Guidelines

- No jargon: avoid "scorer", "pass rate", "LoggedModel" — use "quality check", "performance", "agent"
- Lead with the headline: good news or bad news first, then details
- Actionable: always end with what needs attention
- Honest: do not obscure poor results — executives need to make decisions

## Constraints

- Maximum 1 paragraph + 1 table + action items
- Never expose trace IDs, experiment IDs, or MLflow internals
- If fleet is small (< 3 agents), skip percentages — use counts
- Never `import mlflow` in the sandbox
