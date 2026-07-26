# Design Principles

*Read this before proposing architecture changes or adding new components.*

Agent Lens is the **decision plane** on top of the MLflow **data plane**. Every
design decision follows from this separation. If you find yourself building
something that stores traces, scores content, or registers models — stop. MLflow
already does it.

---

## 1. Data Plane vs. Decision Plane

MLflow owns data. Agent Lens owns decisions.

| MLflow (Consume — Never Rebuild) | Agent Lens (Build on Top) |
|---|---|
| Trace storage | Qualification lifecycle |
| 23 built-in GenAI judges | Scorer profile selection  |
| LoggedModel registry | Qualification state + TTL |
| Token/cost accounting | Fleet-wide cost aggregation |
| Webhooks (15 event types) | CI/CD quality gate (synchronous) |
| Assessments on traces | Governance audit trail |
| Experiment organization | Fleet observatory |

When in doubt, ask: "Does MLflow already store or compute this?" If yes, consume
it via MCP. If no, check the [MLflow Capability Audit](docs/product/mlflow-capability-audit.md)
to verify it truly does not exist before proposing to build it.

---

## 2. Official MCP Only

All MLflow access goes through the **upstream official MLflow MCP server**
(`mlflow mcp run`). This is not negotiable.

**What this means:**
- No `import mlflow` in the sandbox or in skills
- No custom FastMCP wrappers around MLflow APIs
- No direct REST calls to the MLflow tracking server
- The `config.yaml` tool allowlist is the single source of truth for available tools

**Why:**
- Upstream MCP is maintained by the MLflow team — we get new capabilities for free
- The MCP protocol provides a stable contract that survives MLflow API changes
- Sandboxing requires a clean trust boundary — MCP is that boundary
- CI contract tests (`check_mcp_contract.sh`) verify tool availability before deploy

**When a tool is missing:** Contribute it upstream to
[mlflow/mlflow](https://github.com/mlflow/mlflow). Do not fork or wrap.

---

## 3. Skills Over Code

Evaluation logic lives in `SKILL.md` files (structured prompt documents), not in
hardcoded application logic.

**What this means:**
- A skill is a markdown file, not Python code
- Skills declare which MCP tools they use — the allowlist is enforced by CI
- New evaluation workflows are added by writing a new `SKILL.md`, not by modifying
  the Hermes agent source
- The Gateway is the **only** net-new service component with custom code

**Why:**
- Skills are auditable — a security reviewer can read markdown
- Skills are composable — the agent chains them as needed
- Skills are portable — if we switch from Hermes to another harness, skills transfer
- Custom code means custom bugs; skills leverage MLflow's tested judge implementations

**The Gateway exception:** CI/CD pipelines need a synchronous HTTP API. Chat is
async by nature. The Gateway bridges this gap as a thin REST + MCP service. It
calls the same MLflow MCP tools that skills call — it does not embed a separate
evaluation engine.

---

## 4. Score Honestly

GenAI built-in scorers produce **yes/no** categorical results. Agent Lens reports
**pass rates**, never invented Likert scales.

**What this means:**
- "85% pass rate on RelevanceToQuery" — correct
- "4.2 out of 5 on quality" — forbidden (no such scale exists)
- Assessment `state: OK` means the scorer executed — not that the agent answered correctly
- Assessment `feedback.error` means the scorer failed, not that the agent failed
- Always surface scorer **rationale** text — the explanation matters more than the yes/no

**Why:**
- Invented scales create false precision that misleads qualification decisions
- Pass rates are statistically meaningful — "4.2/5" is not
- Agent platform engineers need honest, defensible evidence for governance

**Qualification thresholds:**
- Default pass: ≥ 80% pass rate per required scorer
- Default error ceiling: < 5% scorer failures
- These are configurable — not hardcoded truths

---

## 5. Consume Before Building

Before proposing any new component, check whether MLflow already provides it.
The [MLflow Capability Audit](docs/product/mlflow-capability-audit.md) is the
authoritative reference.

**Examples of "consume" decisions:**
- Agent registry → LoggedModel with qualification tags (not a custom database)
- Cost tracking → `mlflow.llm.cost` span attribute (not a custom cost table)
- Scorer catalog → `list_scorers` MCP tool (not a hardcoded list)
- Version comparison → `search_logged_models` with ordering (not a custom diff engine)
- Tag-based filtering → LoggedModel `filter_string` supports tags (not a custom index)

**Examples of "build" decisions:**
- CI/CD gate → MLflow webhooks are async; pipelines need synchronous pass/fail
- Audit trail → MLflow assessments are mutable and lack actor identity
- Fleet observatory → MLflow is per-experiment; fleet view needs cross-experiment aggregation
- Qualification lifecycle → MLflow has no concept of QUALIFIED/PENDING/EXPIRED states

**The test:** If you can implement a feature using only existing MCP tools + a
SKILL.md file, do that. If you need a REST endpoint, it belongs in the Gateway.
If you need a new MCP tool, contribute it upstream.

---

## 6. Kubernetes-Native Security

Agent Lens is designed for secure enterprise deployment on Kubernetes from day one.
Security is not a layer added later.

**What this means:**
- **Landlock** filesystem sandboxing — the agent process cannot access arbitrary paths
- **NetworkPolicy** isolation — egress restricted to MLflow MCP endpoint only
- **Security Context Constraints** — non-root UID, read-only root filesystem,
  dropped capabilities
- **Immutable container image** — no `pip install` at runtime, no package
  manager in the final image
- **OAuth Proxy** for SSO/OIDC — authentication handled at the infrastructure
  level, not in application code
- **API key auth** for the Gateway — scrypt-hashed, never stored in plaintext

**Why:**
- Enterprise customers require these controls before production approval
- The sandbox model means a compromised skill cannot escalate to cluster access
- "Secure by default" reduces the audit burden for adopters

See [SECURITY.md](SECURITY.md) for the full security model and vulnerability
reporting process.

---

## The Build Boundary in One Diagram

```mermaid
flowchart TB
    subgraph builds ["AGENT LENS BUILDS"]
        GW["Gateway API\nonly net-new service (Python/FastAPI)"]
        Skills["SKILL.md files\nevaluation workflows (markdown)"]
        YAML["YAML configs\nscorer profiles, thresholds"]
        K8s["K8s manifests\ndeploy, NetworkPolicy, OAuth Proxy"]
        Audit["Audit trail\nJSONL + SHA-256 chain (in Gateway)"]
        Note["EVERYTHING ELSE IS CONSUMED\nFROM MLFLOW VIA MCP"]
    end

    builds -->|16 tools| MLflow["MLflow MCP"]
    builds -->|4 tools| GatewayMCP["Gateway MCP"]

    MLflow --> MLflowStore["MLflow Tracking\nTraces, Scorers,\nLoggedModel, Runs"]
    GatewayMCP --> AuditStore["Audit store (JSONL)\nQualification records\nFleet aggregation cache"]
```

---

## Defining References

| Document | What it covers |
|----------|---------------|
| [Identity](docs/product/identity.md) | What Agent Lens is and is not |
| [MLflow Capability Audit](docs/product/mlflow-capability-audit.md) | Build vs. consume for every planned feature |
| [Vision](docs/product/vision.md) | Market context, ICP, north star metrics |
| [Architecture](docs/architecture.md) | Technical implementation details |
| [SECURITY.md](SECURITY.md) | Security model and vulnerability reporting |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute code and skills |
| [AGENTS.md](AGENTS.md) | Instructions for AI coding agents |
