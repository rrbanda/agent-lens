# Agent Lens -- Product Vision and Strategy

*Owner: Product Management*
*Last updated: July 2026*

---

## 1. Vision Statement

Agent Lens is the enterprise quality qualification layer for AI agents on Kubernetes. It gives platform teams the evidence they need to approve, govern, and continuously monitor agents they did not build -- conversationally, enforceably, and at fleet scale.

**One-liner:** Qualify AI agents you didn't build -- from chat verdict to pipeline gate.

---

## 2. Market Context

### 2.1 The Problem

Enterprises are deploying AI agents faster than they can evaluate them. The data is unambiguous:

- 57% of organizations have agents in production (LangChain 2026, n=1,340)
- 88% of agent pilots never reach production (Forrester/Anaconda 2026)
- 50% of enterprises shipped an agent that passed internal evals and then failed customers (VentureBeat 2026, n=157)
- Only 5% fully trust automated evaluation today
- 64% of leaders cite evaluation gaps as the top blocker preventing pilots from graduating

The root cause is structural: 89% of teams have observability (tracing, logging) but only 37% run online evaluations in production. Teams can *see* what agents do but cannot systematically *grade* whether it was good.

### 2.2 Why Existing Tools Are Insufficient

| Category | Tools | Gap for Platform Engineers |
|---|---|---|
| Model evaluation | MLflow, DeepEval, Ragas | Require data science expertise; no qualification workflow |
| Observability | LangSmith, Arize Phoenix, W&B Weave | Tell you what happened, not whether it was acceptable |
| Vendor-native | Agentforce, Copilot Studio | Locked to one agent ecosystem; not for heterogeneous fleets |
| Benchmarks | SWE-bench, GAIA, AgentBench | Pre-deployment only; do not monitor production |
| Governance | AEGIS, CAGE-1 | Frameworks, not tooling |

No tool today gives a platform engineer a single surface to evaluate agents across frameworks, enforce quality gates in CI/CD, and maintain a governance trail -- without requiring them to become an ML engineer.

### 2.3 Where Agent Lens Wins

Agent Lens occupies a unique position at the intersection of three properties:

```
                    Conversational
                         |
                    Agent Lens
                    /          \
            MLflow-native    Kubernetes-native
```

**Conversational:** Natural-language interaction for evaluation, not dashboards-then-SQL. A platform engineer asks "Can this agent be deployed?" and gets a qualification verdict with evidence, not a data table they must interpret.

**MLflow-native:** All evaluation data flows through upstream official MLflow MCP. No proprietary scoring engine, no vendor lock-in on the eval side. MLflow is the industry standard (30M+ PyPI downloads/month); Agent Lens is the qualification layer on top.

**Kubernetes-native:** Deployed as an OpenShell Sandbox with Landlock + seccomp, NetworkPolicy-isolated, RBAC-integrated. Runs on any conformant Kubernetes distribution (OpenShift, EKS, GKE, vanilla K8s).

---

## 3. Strategic Positioning

### 3.1 What Agent Lens Is

- A **qualification layer** that turns MLflow traces into enforceable quality verdicts
- A **governance record** that creates auditable trails of every qualification decision
- A **fleet observatory** that surfaces quality, cost, and reliability across all agents
- A **conversational interface** that makes evaluation accessible to platform teams

### 3.2 What Agent Lens Is Not

- Not an MLflow replacement or alternative UI
- Not a scoring engine (MLflow GenAI scorers do the evaluation)
- Not an agent framework (works with any framework that produces MLflow traces)
- Not an observability platform (works on top of MLflow tracing and Prometheus)

### 3.3 Competitive Moat

| Dimension | Agent Lens | LangSmith | Arize Phoenix | Agentforce |
|---|---|---|---|---|
| Framework-agnostic | Yes (any MLflow-traced agent) | LangChain ecosystem primarily | Yes | Salesforce only |
| Conversational eval | Yes (chat-first) | No (dashboard-first) | No (dashboard-first) | Partial (Observability Agent) |
| CI/CD gate | M2 (webhook API) | Manual annotation | No | Testing Center only |
| Kubernetes-native | Yes (Sandbox, NetworkPolicy, Pod Security) | No | Self-hosted possible | No |
| Governance trail | M2 (audit log) | Annotation history | No | Session tracing |
| Cost | OSS (Apache 2.0) | $39/seat/mo | Free / $50/mo | Included with Agentforce |

---

## 4. Ideal Customer Profile

### 4.1 Primary ICP (M1-M2)

**Platform engineers** at enterprises with 50+ deployed agents across multiple teams.

They did not build these agents. They must approve them. They need evidence, not opinions.

Characteristics:
- Responsible for agent fleet health, not individual agent development
- Have MLflow already deployed (standalone, RHOAI, or Databricks-managed)
- Operate under internal governance requirements (even if informal)
- Evaluate agents across multiple frameworks (LangChain, CrewAI, custom, etc.)
- Do not have time to build custom evaluation pipelines per agent

### 4.2 Expanded ICP (M3+)

| Persona | Enters At | What They Need From Agent Lens |
|---|---|---|
| Platform Engineer | M1 (current) | Qualification, fleet observatory, trace review |
| AI/ML Engineer | M2 | CI/CD gate integration, eval-in-pipeline, regression tracking |
| Engineering Director / CTO | M3 | Executive dashboard, ROI metrics, fleet health summary |
| CISO / Security Lead | M3 | Governance audit trail, policy violation tracking, agent registry |
| Business Unit Owner | M4 | Adoption metrics, quality trends for their team's agents |
| Compliance / GRC | M4 | Regulatory mapping, qualification export, drift detection |

---

## 5. Persona Expansion Strategy

### Phase 1: Deepen the Wedge (M2)

Harden the platform engineer experience and add the AI/ML engineer as a second persona. The CI/CD gate is the bridge -- platform engineers set the quality bar, AI/ML engineers integrate it into their pipelines.

### Phase 2: Widen to Leadership (M3)

Add executive dashboards and CISO governance views. These personas consume Agent Lens data but rarely interact conversationally. They need periodic reports and alerting, not chat sessions.

### Phase 3: Extend to Business (M4)

Business unit owners and compliance officers. These require the least technical depth but the highest auditability. Qualification exports, regulatory mapping, adoption trends.

The critical constraint: **each persona expansion must produce value from data already flowing through MLflow MCP.** No persona should require a new data collection pipeline.

---

## 6. North Star Metrics

### 6.1 Product Success Metrics (Agent Lens itself)

| Metric | Definition | Target (12 months) |
|---|---|---|
| Agents qualified | Distinct MLflow experiments with at least one qualification verdict | 100+ across 10+ enterprise deployments |
| Qualification-to-gate adoption | % of qualified agents with CI/CD gate enforcement | >40% of qualified agents |
| Fleet coverage | % of MLflow experiments visible in the Observatory | >80% per cluster |
| Time-to-first-qualification | Minutes from first trace to first qualification verdict | <30 minutes |
| Evaluation accuracy | % of qualification verdicts confirmed correct by human review | >90% |

### 6.2 Customer Success Metrics (outcomes for users)

| Metric | Definition | Target |
|---|---|---|
| Pilot-to-production conversion | Agents moving from pilot to production with Agent Lens qualification | >30% (vs. 12% industry baseline) |
| Mean time to detect quality regression | Time from regression occurrence to alert/detection | <1 hour |
| Governance audit pass rate | % of qualification decisions with complete audit trail | 100% for M2+ deployments |
| Agent fleet quality score | Aggregate pass rate across all qualified agents | >85% fleet-wide |

---

## 7. Upstream MCP Strategy

Agent Lens is architecturally MCP-first. Expanding enterprise capabilities requires additional MCP data sources beyond MLflow.

### 7.1 MCP Dependency Map

| MCP Server | Data Provided | Agent Lens Features Enabled | Timeline |
|---|---|---|---|
| **MLflow MCP** (current) | Traces, experiments, evaluations, feedback | All current skills + qualification + CI gate | M1 (done) |
| **Prometheus/Thanos MCP** | Infrastructure metrics, SLOs, token cost signals | Cost-per-agent, latency SLOs, resource utilization | M3 |
| **Kubernetes/OpenShift MCP** | Pod status, deployments, namespaces, labels | Agent registry auto-discovery, deployment status, fleet inventory | M3 |

### 7.2 Agent Lens Gateway API (new component, M2)

The CI/CD quality gate cannot be implemented as a Hermes chat skill -- pipelines need a synchronous HTTP API. Agent Lens Gateway is a thin REST + MCP service that:

- Accepts synchronous requests from CI/CD pipelines (Tekton, GitHub Actions, GitLab CI)
- Calls MLflow MCP to run evaluation
- Returns a structured pass/fail verdict with evidence
- Logs the gate decision to a checksummed audit trail
- Exposes its own MCP server for Hermes (audit + registry tools)

The Gateway is the **only net-new service** Agent Lens builds. Per the [MLflow Capability Audit](mlflow-capability-audit.md), everything else is either a SKILL.md file, a YAML config, or a K8s manifest. See [Identity](identity.md) for the definitive build vs. consume boundary.

### 7.3 MLflow MCP Expansion (M2)

The [MLflow Capability Audit](mlflow-capability-audit.md) identified 5 additional MLflow MCP tools needed for agent registry (LoggedModel tools). M2 expands from 11 to 16 MLflow MCP tools by setting `MLFLOW_MCP_TOOLS=all` and adding `search_logged_models`, `get_logged_model`, `set_logged_model_tags`, `create_logged_model`, and `create_external_model` to the tool allowlist. Agent registry uses LoggedModel as its storage layer (not a custom store).

---

## 8. Technical Principles (Unchanged)

These design decisions from M1 carry forward as product principles:

1. **Official MCP only** -- all MLflow access through upstream MCP tools, never direct SDK calls in the sandbox
2. **Skill-driven methodology** -- evaluation logic lives in skills, not hardcoded application logic
3. **Harness-pluggable** -- Agent Lens is not permanently married to Hermes
4. **Score honestly** -- GenAI scorers are yes/no categorical; report pass rates, never invented Likert scales
5. **MCP-first for new data** -- when Agent Lens needs new data (Prometheus, Kubernetes), add an MCP, not a direct integration
6. **Qualification is evidence, not opinion** -- every verdict must cite scorer results, never assert quality without evaluation

---

## 9. Risk and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| MLflow MCP upstream changes break Agent Lens | High -- all features depend on MCP contract | CI contract check (`check_mcp_contract.sh`), pin to known tool versions |
| Enterprises need >20 experiment fleet scans | Medium -- current skill caps at 20 | M3 introduces pagination and caching in fleet skill |
| Judge LLM quality affects qualification accuracy | High -- Agent Lens relies on MLflow GenAI scorers | Document judge model requirements; surface scorer error rates prominently |
| Single-replica Hermes cannot scale | Medium -- blocks multi-tenant | M3 introduces stateless session design + shared PVC or external store |
| Competitive pressure from vendor-native tools | Medium -- Agentforce, Copilot Studio embed eval | Differentiate on framework-agnostic + Kubernetes-native + conversational |
