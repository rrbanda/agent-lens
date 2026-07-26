---
sidebar_position: 5
title: Roadmap
---

# Roadmap

| Milestone | Goal | Status |
|-----------|------|--------|
| **M0 — Upstream Foundation** | CI, contracts, immutable deploy path | ✅ Done |
| **M1 — MVP Pilot** | 7 skills verified, GenAI eval, qualification verdicts | ✅ Done |
| **M2 — Production Hardening** | CI/CD gate, SSO, audit trail, agent registry | In Progress |
| **M3 — Platform Scale** | Multi-tenant, cost tracking, alerting | Planned |
| **M4 — Enterprise Governance** | Compliance export, regulatory mapping | Planned |
| **M5 — Ecosystem** | Multi-cluster federation, marketplace | Future |

## M1 Deliverables (Completed)

- [x] 7 skills working end-to-end with Hermes + MLflow MCP
- [x] 41 integration tests against real MLflow data
- [x] OpenShell sandbox deployment on OpenShift
- [x] Correct MLflow MCP 3.14 tool names across all configs
- [x] Seed data tooling for local development
- [x] Zero-code agent instrumentation (`usercustomize.py`)

## M2 Roadmap

- [ ] Gateway MCP server (FastAPI)
- [ ] CI/CD quality gate REST endpoint
- [ ] Append-only audit trail with SHA-256 chain
- [ ] Agent registry backed by MLflow LoggedModel
- [ ] SSO integration (OpenShift OAuth)
- [ ] Scorer profile YAML configuration
