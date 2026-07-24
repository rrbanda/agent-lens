# Enterprise readiness

Honest status of Agent Lens for production / enterprise pilots on OpenShift AI (RHOAI).

## What “production-grade” means here

| Capability | Status | Notes |
|------------|--------|-------|
| Official MLflow MCP only | **Done** | No custom FastMCP; `mlflow-mcp` prerequisite |
| Accurate GenAI scoring language | **Done** | Pass rates (yes/no), not fake `/5` Likert |
| MCP-first skills (no sandbox SDK) | **Done** | Soul + skills enforce |
| Auth secrets bootstrap | **Done** | `make secret` → LLM + dashboard/API |
| NetworkPolicy + non-root + drop caps | **Done** | Deploy manifests |
| Skill alignment CI | **Done** | `.github/workflows/ci.yml` |
| Immutable Hermes image | **Done** | `make build-agent` → ImageStream; pod never pip-installs |
| Demo / first-trace runbooks | **Done** | `docs/demo-script.md`, `first-trace.md`, `operator-mcp.md` |
| Session analysis skill | **Done** | `analyze-session` |
| CI/CD quality gate webhook | **Roadmap** | [#18](https://github.com/rrbanda/agent-lens/issues/18) |
| SSO / OIDC for dashboard | **Roadmap** | [#17](https://github.com/rrbanda/agent-lens/issues/17) |
| Multi-tenant isolation | **Roadmap** | [#23](https://github.com/rrbanda/agent-lens/issues/23) |
| Audit trail of certify decisions | **Roadmap** | [#19](https://github.com/rrbanda/agent-lens/issues/19) |
| HA / multi-replica Hermes | **Not yet** | Sticky sessions / shared PVC constraints |

## Production deploy checklist

1. Official `mlflow-mcp` healthy — [operator-mcp.md](operator-mcp.md)
2. `make secret` (never commit real keys)
3. Build + deploy baked image (required — no startup installs):
   ```bash
   make secret          # once
   make build-agent     # OpenShift BuildConfig from Containerfile
   make deploy-agent
   ```
4. Seed traces — [first-trace.md](first-trace.md)
5. `make check-mcp` / demo preflight — [demo-script.md](demo-script.md)
6. Certification uses **≥80% pass rate**, error rate **&lt;5%** — see skills

## Enterprise gaps (do not oversell)

- Chat **certification ≠ pipeline block** until #18 ships
- Regression **tags ≠ Evaluation Dataset API**
- Single-namespace pilot topology (not hard multi-tenant)
- Judge/LLM dependency lives on the MLflow / MCP side

See [limitations.md](limitations.md).

## Recommended pilot bar (MVP enterprise)

Ship a **controlled pilot** when:

- [ ] Official MCP contract check passes
- [ ] Secrets managed via K8s Secrets (not ConfigMap)
- [ ] At least one real agent produces traces + CERTIFIED/NOT CERTIFIED report
- [ ] Observatory does not invent `/5` scores
- [ ] Baked image OR accepted bootstrap risk documented
- [ ] SSO/CI-gate accepted as follow-on (#17 / #18)
