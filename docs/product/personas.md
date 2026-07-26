# Agent Lens -- Persona Definitions

*Owner: Product Management*
*Last updated: July 2026*
*Research basis: [agent-quality-research.md](../agent-quality-research.md)*

---

## Overview

Agent Lens serves six enterprise personas across its roadmap. Each persona asks a fundamentally different question about agent quality, needs different metrics, and enters the product at a different milestone.

This document defines each persona, maps their specific needs to Agent Lens features, and tracks current vs. planned coverage.

---

## Persona 1: Platform Engineer / Agent Platform Operator

**Enters:** M1 (current, primary persona)

### Profile

| Attribute | Detail |
|---|---|
| Title | Platform Engineer, SRE, ML Platform Admin |
| Reports to | Engineering Director or VP of Platform |
| Daily tools | OpenShift console, Prometheus/Grafana, MLflow, terminal |
| Agent relationship | Did not build the agents; must approve and monitor them |
| Decision rights | Can block deployment, set quality bars, escalate to security |

### Primary Question

"Is this fleet reliable, observable, and cost-effective -- and can I qualify this agent for production?"

### Metrics That Matter

| Priority | Metric | Agent Lens Feature | Status |
|---|---|---|---|
| P0 | Task success rate (by intent and tool) | `evaluate-agent` skill (pass rates via GenAI scorers) | M1 -- Done |
| P0 | Qualification verdict (QUALIFIED / NOT QUALIFIED) | `evaluate-agent` skill (>=80% pass rate threshold) | M1 -- Done |
| P0 | Fleet health (HEALTHY / WARNING / CRITICAL / INACTIVE) | `quality-dashboard` skill | M1 -- Done |
| P0 | Trace forensics (error patterns, latency, tokens) | `trace-explorer` + `review-trace` skills | M1 -- Done |
| P1 | CI/CD quality gate (enforceable block) | Agent Lens Gateway API | M2 -- Planned |
| P1 | Regression tracking | `create-regression` skill (expectations + tags) | M1 -- Partial |
| P1 | Escalation rate / tool error rate | Enhanced `trace-explorer` with aggregation | M2 -- Planned |
| P2 | Cost per agent (token + infra) | Cost tracking skill (requires Prometheus MCP) | M3 -- Planned |
| P2 | Drift detection (quality regression over time) | Trend analysis skill | M3 -- Planned |

### Current Coverage

```
M1 Coverage: ██████████░░░░░ ~65%
```

The platform engineer can evaluate, review, annotate, and view fleet health today. What is missing is enforcement (CI/CD gate), cost visibility, and temporal trend analysis.

### User Stories (Current)

- "Evaluate outreach-agent using the tool-calling profile" -- works today
- "Show me the last 20 traces for the billing agent" -- works today
- "Give me a quality dashboard across all agents" -- works today (capped at 20 experiments)
- "What went wrong with this trace?" -- works today

### User Stories (Needed)

- "Block the pipeline if the agent drops below 80% tool call correctness" -- needs CI/CD gate (M2)
- "How much is the support agent costing us per task?" -- needs cost tracking (M3)
- "Alert me if quality drops below baseline" -- needs alerting (M3)

---

## Persona 2: AI / ML Engineer (Agent Builder)

**Enters:** M2

### Profile

| Attribute | Detail |
|---|---|
| Title | ML Engineer, AI Engineer, Agent Developer |
| Reports to | Engineering Manager or ML Lead |
| Daily tools | IDE (Cursor, VS Code), MLflow, CI/CD pipeline, Python |
| Agent relationship | Built the agent; needs to validate before requesting platform approval |
| Decision rights | Can iterate on agent design, fix evaluation failures, request qualification |

### Primary Question

"Is my agent's reasoning correct, efficient, and debuggable -- and will it pass the platform team's quality gate?"

### Metrics That Matter

| Priority | Metric | Agent Lens Feature | Status |
|---|---|---|---|
| P0 | Goal fulfillment | Scorer pass rates via `evaluate-agent` | M1 -- Done (basic) |
| P0 | CI/CD gate integration | Gateway API with webhook + CLI | M2 -- Planned |
| P0 | Eval-in-pipeline (pre-merge) | Gateway API triggered by PR/pipeline | M2 -- Planned |
| P1 | Tool selection / calling accuracy | `evaluate-agent` with tool-calling profile | M1 -- Done |
| P1 | Failure cluster analysis | Enhanced `review-trace` with pattern grouping | M3 -- Planned |
| P1 | Hallucination rate | Groundedness scorer via MLflow | M1 -- Done (RAG profile) |
| P2 | Plan quality / plan adherence (GPA-style) | New skill leveraging GPA-aligned scorers | M4 -- Planned |
| P2 | Execution efficiency | Token-per-task trend via enhanced trace analysis | M3 -- Planned |

### Current Coverage

```
M1 Coverage: ████░░░░░░░░░░░ ~30%
```

The AI/ML engineer can use Agent Lens conversationally to evaluate their agent, but the critical workflow -- evaluation integrated into their CI/CD pipeline -- does not exist yet. M2 is the inflection point for this persona.

### User Stories (Needed)

- "Run the tool-calling profile against my agent's last 50 traces and fail the PR if pass rate drops below 85%"
- "Show me which failure patterns are most common across the last week's traces"
- "Compare the eval results between my v1.2 and v1.3 agent versions"
- "Add this failing trace to the regression suite so it's checked on every release"

---

## Persona 3: Engineering Director / CTO

**Enters:** M3

### Profile

| Attribute | Detail |
|---|---|
| Title | Director of Engineering, VP of AI, CTO |
| Reports to | C-suite or Board |
| Daily tools | Dashboards, Slack, email, quarterly reviews |
| Agent relationship | Sponsors the agent program; accountable for ROI and risk |
| Decision rights | Budget allocation, program continuation, staffing |

### Primary Question

"Is this investment paying off -- and what is the risk exposure across our agent fleet?"

### Metrics That Matter

| Priority | Metric | Agent Lens Feature | Status |
|---|---|---|---|
| P0 | Fleet-wide quality score (aggregate pass rate) | Executive summary skill | M2 -- Planned |
| P0 | Total cost of agent fleet (compute + human escalation) | Cost dashboard (Prometheus MCP) | M3 -- Planned |
| P0 | Agents qualified vs. total deployed | Registry + qualification history | M2 -- Planned |
| P1 | Time-to-value acceleration | Before/after workflow metrics | M4 -- Planned |
| P1 | Containment rate (% handled without humans) | Derived from escalation tracking | M3 -- Planned |
| P2 | ROI per agent / per team | Cost attribution + business outcome correlation | M4 -- Planned |

### Current Coverage

```
M1 Coverage: █░░░░░░░░░░░░░░ ~10%
```

The quality-dashboard skill provides a basic fleet view, but it is designed for platform engineers, not executives. This persona needs a periodic summary report, not an interactive chat session.

### User Stories (Needed)

- "Give me a weekly executive report on agent fleet health, cost, and qualification status"
- "Which teams have unqualified agents in production?"
- "What is our fleet-wide quality trend over the last quarter?"
- "How much are we spending on agent compute vs. the business value delivered?"

---

## Persona 4: CISO / Security and Risk Leader

**Enters:** M3

### Profile

| Attribute | Detail |
|---|---|
| Title | CISO, Security Architect, Risk Manager |
| Reports to | CIO or CEO |
| Daily tools | SIEM, vulnerability scanners, audit platforms, policy engines |
| Agent relationship | Must ensure agents do not create security or compliance risk |
| Decision rights | Can block deployment on security grounds, mandate governance controls |

### Primary Question

"Can I trust this agent not to harm the organization -- and can I prove it to auditors?"

### Metrics That Matter

| Priority | Metric | Agent Lens Feature | Status |
|---|---|---|---|
| P0 | Agent inventory (complete fleet registry) | Agent Registry (MLflow LoggedModel + manual) | M2 -- Planned |
| P0 | Audit trail of all qualification decisions | Audit log (every qualify/reject with evidence) | M2 -- Planned |
| P0 | Policy violation rate | Safety scorer tracking + trend | M3 -- Planned |
| P1 | Per-agent identity and permission boundaries | Registry metadata + RBAC integration | M3 -- Planned |
| P1 | Sensitive data exposure detection | PII/PHI scanner in trace review | M4 -- Planned |
| P1 | Adversarial robustness (red team results) | Red team evaluation profile | M4 -- Planned |
| P2 | Configuration drift (approved vs. running) | Drift detection skill (K8s MCP comparison) | M4 -- Planned |
| P2 | Mean time to detect unsafe behavior | Alert-to-containment SLO tracking | M4 -- Planned |

### Current Coverage

```
M1 Coverage: ░░░░░░░░░░░░░░░ ~5%
```

Agent Lens has no governance or audit features today. The only security-relevant capability is that qualification decisions are logged in Hermes session history (PVC), but this is not a proper audit trail. M2 introduces the audit trail; M3 introduces the agent registry and policy violation tracking.

### User Stories (Needed)

- "Show me a complete inventory of all agents on this cluster with their qualification status"
- "Export the audit trail of all qualification decisions for the last quarter"
- "Which agents have not been re-evaluated in the last 30 days?"
- "Flag any agent that has a safety scorer pass rate below 95%"

---

## Persona 5: Business Unit Owner / Line-of-Business Leader

**Enters:** M4

### Profile

| Attribute | Detail |
|---|---|
| Title | VP of Sales, Head of Support, Business Operations Director |
| Reports to | C-suite |
| Daily tools | CRM, support platform, business dashboards |
| Agent relationship | Owns the business process the agent serves; cares about outcomes |
| Decision rights | Can request agent changes, approve business workflows |

### Primary Question

"Does this agent actually make my team's work better?"

### Metrics That Matter

| Priority | Metric | Agent Lens Feature | Status |
|---|---|---|---|
| P0 | Acceptance rate (user action on agent output) | User interaction analytics (requires trace metadata) | M4 -- Planned |
| P0 | Task completion rate (FCR equivalent) | Derived from trace success rates + session analysis | M4 -- Planned |
| P1 | Quality score trend (improving / declining) | Trend analysis on qualification history | M3 -- Partial |
| P1 | Time-to-complete (agent-assisted vs. baseline) | Before/after comparison dashboard | M4 -- Planned |
| P2 | CSAT delta (before vs. after agent deployment) | External survey integration | M5 -- Planned |

### Current Coverage

```
M1 Coverage: ░░░░░░░░░░░░░░░ ~0%
```

Agent Lens has no business-user features today. This persona requires the least technical depth but the highest interpretability -- simple trend lines, not scorer details.

### User Stories (Needed)

- "Is our support agent getting better or worse over the last month?"
- "What percentage of customer interactions are fully handled by the agent?"
- "Show me the quality trend for the agents my team owns"

---

## Persona 6: Compliance / Legal / GRC Leader

**Enters:** M4

### Profile

| Attribute | Detail |
|---|---|
| Title | Chief Compliance Officer, GRC Analyst, Legal Counsel |
| Reports to | General Counsel or CRO |
| Daily tools | GRC platforms, audit management, regulatory databases |
| Agent relationship | Must ensure agents comply with regulations and internal policy |
| Decision rights | Can mandate controls, block non-compliant deployments |

### Primary Question

"Can I defend this agent's behavior in front of a regulator?"

### Metrics That Matter

| Priority | Metric | Agent Lens Feature | Status |
|---|---|---|---|
| P0 | Qualification evidence export (PDF / structured) | Compliance export skill | M4 -- Planned |
| P0 | Audit log completeness (who, what, when, which policy) | Audit trail (builds on M2 foundation) | M4 -- Planned |
| P1 | Regulatory control mapping (ISO 42001, SOX, etc.) | Compliance mapping metadata on qualifications | M4 -- Planned |
| P1 | Agent configuration drift | Drift detection (approved vs. running comparison) | M4 -- Planned |
| P2 | Data residency adherence | Trace metadata + deployment topology verification | M5 -- Planned |
| P2 | Retention schedule compliance | Trace lifecycle management | M5 -- Planned |

### Current Coverage

```
M1 Coverage: ░░░░░░░░░░░░░░░ ~0%
```

No compliance features exist today. The M2 audit trail is the foundation; M4 adds export and regulatory mapping.

### User Stories (Needed)

- "Export a compliance report for all agents qualified in Q2 with full evidence chains"
- "Map our agent qualifications to ISO 42001 control requirements"
- "Which agents have drifted from their approved configuration?"
- "Show me the complete decision history for the billing agent -- every evaluation, every verdict, every annotation"

---

## Persona Coverage Summary

| Persona | M1 (Current) | M2 | M3 | M4 | M5 |
|---|---|---|---|---|---|
| Platform Engineer | 65% | 85% | 95% | 95% | 100% |
| AI/ML Engineer | 30% | 70% | 85% | 90% | 95% |
| Engineering Director / CTO | 10% | 30% | 70% | 85% | 95% |
| CISO / Security Lead | 5% | 40% | 65% | 85% | 95% |
| Business Unit Owner | 0% | 5% | 20% | 60% | 80% |
| Compliance / GRC | 0% | 10% | 20% | 65% | 85% |

### Coverage Visualization

```
M1  PE  ██████░░░░  AI  ███░░░░░░░  CTO █░░░░░░░░░  CISO ░░░░░░░░░░
M2  PE  ████████░░  AI  ███████░░░  CTO █░░░░░░░░░  CISO ██░░░░░░░░
M3  PE  █████████░  AI  ████████░░  CTO ███████░░░  CISO ██████░░░░
M4  PE  █████████░  AI  █████████░  CTO ████████░░  CISO ████████░░
```

---

## Cross-Persona Feature Dependencies

Some features serve multiple personas simultaneously. The table below maps features to their primary and secondary consumers.

| Feature | Primary Persona | Secondary Personas | Milestone |
|---|---|---|---|
| Qualification verdict | Platform Engineer | AI/ML Engineer | M1 (done) |
| Trace review / annotation | Platform Engineer | AI/ML Engineer | M1 (done) |
| Fleet observatory | Platform Engineer | CTO, CISO | M1 (done) |
| CI/CD quality gate | AI/ML Engineer | Platform Engineer | M2 |
| Audit trail | CISO | Compliance, Platform Engineer | M2 |
| SSO/OIDC | Platform Engineer | All personas | M2 |
| Agent registry | CISO | Platform Engineer, CTO | M2 |
| Executive summary | CTO | Business Owner | M2 |
| Cost tracking | Platform Engineer | CTO | M3 |
| Alerting / drift detection | Platform Engineer | CISO | M3 |
| Compliance export | Compliance | CISO, CTO | M4 |
| Adoption metrics | Business Owner | CTO | M4 |
| Regulatory mapping | Compliance | CISO | M4 |
