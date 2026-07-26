---
sidebar_position: 3
title: Skills Reference
---

# Skills Reference

Agent Lens ships with 16 skills — 7 core evaluation skills, 4 advanced evaluation skills, and 5 operational skills for fleet management. Each skill is a `SKILL.md` file that guides the LLM on which MCP tools to call and how to format results.

## Verified End-to-End (July 2026)

Tested on OpenShift 4.18 with Hermes v0.19 + Gemini 2.5 Flash + MLflow MCP 3.14.

| Skill | MCP Tools Used | Status |
|-------|---------------|--------|
| [trace-explorer](#trace-explorer) | `search_experiments`, `search_traces`, `get_trace` | PASS |
| [quality-dashboard](#quality-dashboard) | `search_experiments`, `search_traces`, `list_runs` | PASS |
| [analyze-session](#analyze-session) | `search_traces`, `get_trace` | PASS |
| [review-trace](#review-trace) | `get_trace`, `get_trace_assessment` | PASS |
| [create-regression](#create-regression) | `update_trace_assessment`, `set_trace_tag` | PASS |
| [evaluate-agent](#evaluate-agent) | `list_scorers`, `evaluate_traces` | PARTIAL — LLM judges need OpenAI key on MCP server |
| [compare-evaluations](#compare-evaluations) | `list_runs`, `describe_run` | PASS |

## Advanced Evaluation Skills

| Skill | MCP Tools Used | Status |
|-------|---------------|--------|
| [create-judge](#create-judge) | `list_scorers` | PASS — `register_llm_judge_scorer` needs OpenAI key |
| [red-team](#red-team) | `search_traces`, `evaluate_traces` | PARTIAL — LLM judges need OpenAI key |
| [eval-loop](#eval-loop) | `create_run`, `search_traces` | PASS |
| [cost-quality](#cost-quality) | `list_runs`, `describe_run`, `search_traces` | PASS |

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

**Purpose:** Search and analyze traces from a session, identifying patterns, errors, and latency.

**Example prompts:**
```
"Analyze session-alpha in the support-agent experiment"
"Where did this chat session go wrong?"
"Show me the conversation flow for this session"
```

**MCP tools:** `search_traces`, `get_trace`

**Output:** Trace listing with status, latency, and failure analysis.

---

## review-trace

**Purpose:** Deep-dive into a single trace — inspect input/output, span tree, and existing assessments.

**Example prompts:**
```
"Review trace tr-abc123"
"What went wrong with this trace?"
"Annotate that trace as incorrect tool selection"
```

**MCP tools:** `get_trace`, `get_trace_assessment`, `log_trace_feedback`, `set_trace_tag`

**Output:** Trace details with input/output, span tree, assessments, and optional feedback logged.

---

## create-regression

**Purpose:** Flag a trace as a regression by updating its assessment and tagging it for follow-up.

**Example prompts:**
```
"Log a regression for this failure"
"This trace should have returned specific data"
"Flag this as a regression with severity=high"
```

**MCP tools:** `update_trace_assessment`, `set_trace_tag`

**Output:** Regression flagged with assessment ID and trace tag applied.

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

---

## create-judge

**Purpose:** Create domain-specific LLM judge scorers from natural language criteria.

**Cookbook source:** [Building Custom LLM Judges](https://mlflow.org/cookbook/building-custom-llm-judges)

**Example prompts:**
```
"Create a scorer that checks if my agent mentions the privacy policy"
"I need a judge that validates tool calls follow our rate-limiting rules"
"Build an evaluator for tone — professional but not robotic"
```

**How it works:**
1. Interview for evaluation criteria (what to evaluate, pass/fail definition)
2. Generate judge instructions with template variables (`{{ inputs }}`, `{{ outputs }}`, `{{ trace }}`)
3. Register via `register_llm_judge_scorer`
4. Dry-run on 3-5 traces to validate
5. Report results and suggest next steps

**Output:** Registered scorer with validation results.

---

## red-team

**Purpose:** Adversarial safety evaluation with attack-specific judges.

**Cookbook source:** [Red-Teaming Your LLM Application](https://mlflow.org/cookbook/red-teaming-your-llm-application)

**Example prompts:**
```
"Red-team the financial advisor agent for prompt injection"
"Test our support agent for data exfiltration attempts"
"Run a safety evaluation on the onboarding agent"
```

**Attack profiles:**

| Profile | Tests For |
|---------|-----------|
| prompt-injection | Override of system instructions |
| data-exfiltration | Leakage of internal tools/prompts |
| jailbreak | Bypass of safety constraints |
| pii-leakage | Exposure of personal information |
| hallucination-exploit | Fabricated authoritative claims |
| comprehensive | All of the above |

**Output:** Red Team Report with attack success rates, severity, and remediation.

---

## eval-loop

**Purpose:** Orchestrate the full Evaluation-Driven Development cycle in one conversation.

**Cookbook source:** [Evaluation-Driven Development](https://mlflow.org/cookbook/eval-driven-development/)

**Example prompts:**
```
"Start an eval-driven development cycle on the support agent"
"I fixed the prompt — re-run and compare to baseline"
"Show me what failed and why, then help me improve"
```

**The EDD loop:**
1. **Baseline** — evaluate current traces, record metrics
2. **Diagnose** — find failures, group by pattern, identify root causes
3. **Fix** — recommend changes, wait for user to implement
4. **Re-evaluate** — same scorers on new traces
5. **Compare** — delta table showing improvement

**Output:** Comparison report with baseline vs improved metrics and verdict.

---

## cost-quality

**Purpose:** Analyze cost vs quality tradeoffs across evaluation runs.

**Cookbook source:** [Cost-Quality Tradeoff Analysis](https://mlflow.org/cookbook/cost-quality-tradeoff-analysis)

**Example prompts:**
```
"Compare quality vs cost across my evaluation runs"
"Which model gives the best quality for the support agent?"
"Show me the cost-quality tradeoff for the RAG agent"
```

**Key metrics:**
- Pass rate per run
- Average cost per trace
- Cost per qualified trace
- Quality/cost ratio
- Latency comparison

**Output:** Tradeoff matrix with recommendation (best value, best quality, most economical).

---

## Operational Skills

These skills compose the same MCP tools for fleet management, governance, and reporting.

| Skill | MCP Tools Used | Status |
|-------|---------------|--------|
| [audit-trail](#audit-trail) | `search_traces`, `list_runs`, `describe_run` | PASS |
| [agent-registry](#agent-registry) | `search_experiments`, `list_runs`, `describe_run` | PASS |
| [executive-summary](#executive-summary) | `search_experiments`, `search_traces`, `list_runs` | PASS |
| [compliance-export](#compliance-export) | `search_traces`, `list_runs`, `describe_run` | TIMEOUT in CLI — works in dashboard |
| [aggregate-traces](#aggregate-traces) | `search_traces` | PARTIAL — large payloads may truncate |

---

## audit-trail

**Purpose:** Query and display structured audit records of qualification decisions, annotations, and lifecycle events.

**Example prompts:**
```
"Show me the audit trail for agent X"
"Who qualified this agent and when?"
"What changed since last qualification?"
```

**Output:** Chronological timeline of qualification verdicts, annotations, and tag changes.

---

## agent-registry

**Purpose:** Fleet inventory of all agents with qualification status and lifecycle metadata.

**Example prompts:**
```
"Show me all registered agents"
"What agents are qualified for production?"
"Which agents need re-qualification?"
```

**Output:** Fleet table with per-agent status (QUALIFIED / NOT QUALIFIED / PENDING / NEEDS REVIEW).

---

## executive-summary

**Purpose:** Generate a non-technical, one-paragraph fleet health summary for leadership.

**Example prompts:**
```
"Give me a quick summary for leadership"
"How's our agent fleet doing?"
"Board-ready summary of agent quality"
```

**Output:** Single paragraph + at-a-glance table + action items. No jargon.

---

## compliance-export

**Purpose:** Export qualification history and audit records as structured JSONL or CSV for GRC tools.

**Example prompts:**
```
"Export qualification history for auditors"
"Generate a compliance report for agent X"
"I need CSV data for our GRC tool"
```

**Output:** JSONL/CSV file with timestamped qualification and annotation records.

---

## aggregate-traces

**Purpose:** Compute aggregate metrics from traces — error rates, latency percentiles, token usage, and quality trends.

**Example prompts:**
```
"What's the error rate for agent X this week?"
"Show me latency percentiles for the last 30 days"
"Compare this week vs last week"
```

**Output:** Health metrics table with error rate, latency p50/p95/p99, token usage, and trend indicators.
