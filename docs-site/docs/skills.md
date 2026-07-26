---
sidebar_position: 3
title: Skills Reference
---

# Skills Reference

Agent Lens ships with 7 verified skills. Each skill is a `SKILL.md` file that guides the LLM on which MCP tools to call and how to format results.

## Verified End-to-End (July 2026)

| Skill | MCP Tools | Status |
|-------|-----------|--------|
| [trace-explorer](#trace-explorer) | `search_experiments`, `search_traces`, `get_trace` | ✅ Verified |
| [quality-dashboard](#quality-dashboard) | `search_experiments`, `search_traces`, `list_runs` | ✅ Verified |
| [analyze-session](#analyze-session) | `search_traces` | ✅ Verified |
| [review-trace](#review-trace) | `get_trace`, `log_trace_feedback`, `set_trace_tag` | ✅ Verified |
| [create-regression](#create-regression) | `get_trace`, `log_trace_expectation`, `set_trace_tag` | ✅ Verified |
| [evaluate-agent](#evaluate-agent) | `list_scorers`, `evaluate_traces` | ✅ Verified |
| [compare-evaluations](#compare-evaluations) | `list_runs`, `describe_run` | ✅ Verified |

---

## trace-explorer

**Purpose:** Search and summarize traces from any agent's MLflow experiment.

**Example prompts:**
```
"Show me the last 20 traces for billing-agent"
"Find all ERROR traces in the last 24 hours"
"Get details on trace tr-abc123"
```

**Output:** Tabular summary with trace IDs, status, duration, error counts.

---

## quality-dashboard

**Purpose:** Fleet-wide quality overview across all experiments.

**Example prompts:**
```
"Give me a quality dashboard across all agents"
"Which agents are unhealthy?"
"Show fleet health status"
```

**Output:** Per-agent health status (HEALTHY/WARNING/CRITICAL/INACTIVE) with metrics.

---

## analyze-session

**Purpose:** Reconstruct multi-turn conversation sessions and identify where reasoning broke down.

**Example prompts:**
```
"Analyze session-alpha in the support-agent experiment"
"Where did this chat session go wrong?"
"Show me the conversation flow for this session"
```

**Output:** Session timeline with per-turn outcomes and failure analysis.

---

## review-trace

**Purpose:** Deep-dive into a single trace, render the span tree, and log human feedback.

**Example prompts:**
```
"Review trace tr-abc123"
"What went wrong with this trace?"
"Annotate that trace as incorrect tool selection"
```

**Output:** Span tree visualization, existing assessments, and feedback logged.

---

## create-regression

**Purpose:** Flag a trace as a regression and log expectations for follow-up evaluation.

**Example prompts:**
```
"Log a regression for this failure"
"This trace should have returned specific data"
"Flag this as a regression with severity=high"
```

**Output:** Regression tagged, expectation logged, dataset tag applied.

---

## evaluate-agent

**Purpose:** Run MLflow's GenAI scorers against production traces and produce qualification verdicts.

**Example prompts:**
```
"Evaluate outreach-agent using the RAG profile"
"Can this agent be deployed?"
"List available scorers"
```

**Output:** Quality Qualification Report with pass rates per scorer.

**Scorer Profiles:**

| Profile | Scorers | Use When |
|---------|---------|----------|
| RAG | RelevanceToQuery, RetrievalGroundedness | Agent retrieves docs |
| Tool-Calling | ToolCallCorrectness, ToolCallEfficiency | Agent calls APIs |
| Chat | RelevanceToQuery, Guidelines | General assistant |
| Safety | Guidelines, Safety | Content safety |
| Comprehensive | All scorers | Full assessment |

---

## compare-evaluations

**Purpose:** Compare evaluation runs to track quality trends over time.

**Example prompts:**
```
"Show me the evaluation history for billing-agent"
"Compare the last two eval runs"
"What's the trend in pass rates?"
```

**Output:** Run comparison with metrics, trends, and certification status.
