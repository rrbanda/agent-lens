# Contributing to Agent Lens

Thank you for your interest in contributing to Agent Lens! This document provides guidelines and information for contributors.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.11+
- Access to a Kubernetes cluster with MLflow (for integration testing)
- Upstream official MLflow MCP available in the cluster (`mlflow-mcp`) — see `docs/operator-mcp.md`
- `oc` CLI (for deployment testing)
- Read [DESIGN.md](DESIGN.md) before proposing architecture changes
- Read `docs/limitations.md` before proposing gate/dataset/queue features

### How we track work

All work flows through GitHub Issues and the **[Agent Lens Roadmap](https://github.com/users/rrbanda/projects/3)** project.

| Milestone | Purpose |
|-----------|---------|
| [M0](https://github.com/rrbanda/agent-lens/milestone/1) | Upstream foundation |
| [M1](https://github.com/rrbanda/agent-lens/milestone/2) | MVP pilot |
| [M2](https://github.com/rrbanda/agent-lens/milestone/3) | Production hardening |
| [M3](https://github.com/rrbanda/agent-lens/milestone/4) | Platform scale |
| [M4](https://github.com/rrbanda/agent-lens/milestone/5) | Enterprise governance |
| [M5](https://github.com/rrbanda/agent-lens/milestone/6) | Ecosystem |

**Labels**

| Kind | Labels |
|------|--------|
| Type | `type:bug`, `type:feature`, `type:chore`, `type:docs`, `type:adr` |
| Area | `area:mcp`, `area:hermes`, `area:gateway`, `area:audit`, `area:registry`, `area:instrumentation`, `area:deploy`, `area:ci`, `area:docs`, `area:security` |
| Priority | `P0`, `P1`, `P2` |
| Size | `size:S`, `size:M`, `size:L` |
| Other | `epic`, `good first issue`, `needs-design`, `blocked` |

PRs should reference an issue (`Fixes #N`). Skills must pass `pytest tests/test_skill_alignment.py`.

### Development Setup

```bash
# Clone your fork
git clone https://github.com/<your-username>/agent-lens.git
cd agent-lens

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install test dependencies
pip install pytest pyyaml

# Run tests
pytest
```

### Running Tests

```bash
# All tests
pytest

# Skill alignment only (official MCP allowlist)
pytest tests/test_skill_alignment.py -v

# Gateway tests (M2, requires gateway running)
pytest tests/test_gateway_api.py -v

# MCP contract check (requires cluster access)
scripts/check_mcp_contract.sh
```

## How to Contribute

### Reporting Bugs

Open a [GitHub Issue](https://github.com/rrbanda/agent-lens/issues/new) with:

1. **Summary** — one sentence describing the problem
2. **Environment** — Kubernetes distribution and version, MLflow version, Python version
3. **Steps to reproduce** — minimal steps to trigger the bug
4. **Expected behavior** — what should happen
5. **Actual behavior** — what happens instead
6. **Logs** — relevant pod logs or error messages

### Suggesting Features

Open a [GitHub Issue](https://github.com/rrbanda/agent-lens/issues/new) with:

1. **Problem statement** — what pain point does this address?
2. **Proposed solution** — how would it work?
3. **Alternatives considered** — what else could solve this?

### Pull Requests

1. Fork the repository and create a branch from `main`
2. Make your changes
3. Add or update tests as appropriate
4. Ensure all tests pass (`pytest`)
5. Update documentation if needed
6. Submit a pull request

#### PR Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Skill alignment check passes (`pytest tests/test_skill_alignment.py`)
- [ ] No credentials or secrets in committed code
- [ ] Documentation updated (if adding features)
- [ ] Commit messages are descriptive

## Contribution Areas

### Adding a New Skill

1. Create `agent-lens/skills/<skill-name>/SKILL.md`
2. Reference only official tools allowlisted in `agent-lens/config.yaml` as `mcp_mlflow_<tool>`
3. Add the skill to `agent-lens/deploy/kustomization.yaml` configMapGenerator
4. Add the skill name to the `SKILLS` list in `agent-lens/deploy/deployment.yaml`
5. Run `pytest tests/test_skill_alignment.py` to verify
6. Never include sandbox snippets that `import mlflow`

### Contributing to the Gateway (M2)

The Gateway is a Python/FastAPI service under `gateway/`. It provides the CI/CD
quality gate REST API, audit trail, and a Gateway MCP server for Hermes skills.

1. Routes go in `gateway/api/routes/`
2. Use the Gateway's MCP client to access MLflow — do not `import mlflow`
3. Log governance decisions to the audit trail with `log_audit_event`
4. Add tests in `tests/test_gateway_*.py`
5. Update Gateway MCP tool definitions if the endpoint should be callable from skills

Key Gateway endpoints (M2):

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/gate/evaluate` | Synchronous CI/CD quality gate |
| `GET /api/v1/audit` | Query audit trail |
| `GET /api/v1/registry` | Agent fleet registry |
| `POST /api/v1/registry` | Register an agent |

### Contributing to the Audit Trail (M2)

The audit trail is append-only JSONL with SHA-256 hash chain. Constraints:

- No update or delete operations — append only
- Every entry must include actor identity (from SSO/API key)
- Every entry's hash must reference the previous entry's hash
- Export formats: JSON Lines, CSV for GRC tools

### Contributing to the Agent Registry (M2)

The agent registry uses MLflow LoggedModel as its storage layer — there is no
custom registry database. Agent Lens adds qualification lifecycle tags on top:

- `agentlens.qualification.status` — QUALIFIED / PENDING / EXPIRED
- `agentlens.qualification.timestamp` — ISO-8601
- `agentlens.qualification.ttl_days` — re-qualification window
- `agentlens.qualification.scorer_profile` — which profile was used

### Extending MCP capabilities

Agent Lens does **not** ship a custom MCP server (except the Gateway MCP for
audit + registry tools). New MLflow MCP tools belong
[upstream in MLflow](https://mlflow.org/docs/latest/genai/mcp/). After an upstream
tool ships:

1. Add it to `agent-lens/config.yaml` `tools.include`
2. Update skills / `soul.md` to call `mcp_mlflow_<tool>`
3. Run skill alignment tests

### Adding a Deployment Target

1. Create `agent-lens/deploy/overlays/<target>/kustomization.yaml`
2. Override environment-specific values (MCP URL, image, resources)
3. Document in the README under "Getting Started"

## Style Guide

### Python

- Follow PEP 8
- Use type hints for function parameters
- No credentials or environment-specific values in code

### Kubernetes Manifests

- Use kustomize for configuration management
- Secrets as placeholder templates (never commit real values)
- Always include resource requests/limits
- Security contexts on all pods

### Documentation

- Diagrams as inline Mermaid with `%%{init: {'theme': 'neutral'}}%%`
- No external image files for architecture diagrams
- Keep README focused on getting started; details go in `docs/`

## Architecture Decisions

Key decisions are documented in [DESIGN.md](DESIGN.md) and `docs/architecture.md`.
When proposing changes that affect architecture, please:

1. Read [DESIGN.md](DESIGN.md) for the six design principles
2. Check the [MLflow Capability Audit](docs/product/mlflow-capability-audit.md)
   to verify you are not duplicating MLflow capabilities
3. Reference or update the appropriate document in your PR

**Product rule:** Hermes always uses upstream official MLflow MCP — do not reintroduce a custom FastMCP package as the default path.

## Release Process

Releases follow semantic versioning:
- **Patch** (0.1.x) — bug fixes, dependency updates
- **Minor** (0.x.0) — new skills, features
- **Major** (x.0.0) — breaking changes to skill / MCP allowlist contract

## For AI Coding Agents

See [AGENTS.md](AGENTS.md) for specific instructions on constraints, repository
structure, and common mistakes to avoid.

## Questions?

- Open a [Discussion](https://github.com/rrbanda/agent-lens/discussions) for questions
- Open an [Issue](https://github.com/rrbanda/agent-lens/issues) for bugs or feature requests
