# AI Coding Agent Instructions

This file tells AI coding agents (Cursor, Claude Code, Codex, etc.) how to
contribute to Agent Lens correctly. Read this before generating code or skills.

---

## Repository Structure

```
agent-lens/
├── agent-lens/              # Agent runtime (skills, soul, config, deploy)
│   ├── soul.md              # Agent identity and constraints — DO NOT MODIFY without understanding
│   ├── config.yaml          # MCP URL, tool allowlist — DO NOT MODIFY without understanding
│   ├── Containerfile        # Container image definition
│   ├── skills/              # SKILL.md files (evaluation workflows)
│   └── deploy/              # OpenShift manifests (kustomize)
│       └── openshell/       # OpenShell Sandbox deployment
├── instrumentation/         # Zero-code autolog + CLI eval helper
│   ├── usercustomize.py     # Drop-in autolog for target Python agents
│   └── eval_agent.py        # Offline CLI evaluation helper
├── tests/                   # Contract tests
│   └── test_skill_alignment.py  # Skill ↔ MCP allowlist alignment
├── scripts/                 # Operator helpers
│   └── check_mcp_contract.sh   # MCP tool availability check
├── docs/                    # Architecture, ops guides, limitations
│   └── product/             # Vision, identity, PRDs, roadmap, audit
└── vendor/mlflow-skills/    # Upstream reference patterns (submodule)
```

---

## Critical Constraints

### 1. Only allowlisted MCP tools in skills

Skills may reference **only** tools from the `config.yaml` allowlist:

- `mcp_mlflow_*` — official MLflow MCP tools

Never reference a tool that is not in the allowlist. If you need a tool that does
not exist, it must be contributed upstream to MLflow.

### 2. Never `import mlflow` in the sandbox

The Agent Lens sandbox does not have the MLflow SDK installed. All MLflow access goes
through MCP. Code that calls `mlflow.search_experiments()` directly will fail at
runtime.

The **only** place `import mlflow` is valid is in `instrumentation/` — those files
run on the **target agent**, not in the sandbox.

### 3. Never invent scoring scales

GenAI scorers return **yes/no** categorical values. Skills must report **pass rates**
(e.g., "85% pass rate on RelevanceToQuery"). Never output "4.2/5" or any Likert
scale — no such scale exists in the scoring system.

### 4. Immutable container image

The Containerfile does not include a package manager in the final stage. Do not
add `pip install` commands that run at container startup. All dependencies must be
installed at build time.

---

## How to Add a Skill

1. Create `agent-lens/skills/<skill-name>/SKILL.md`
2. Reference only tools from the `config.yaml` allowlist as `mcp_mlflow_<tool>`
   or `mcp_agentlens_<tool>`
3. Add the skill to `agent-lens/deploy/openshell/kustomization.yaml` configMapGenerator
4. Add the skill name to the deploy manifests
5. Run `pytest tests/test_skill_alignment.py` to verify tool alignment

### Skill template

```markdown
# <Skill Name>

## Purpose
<One sentence: what this skill does.>

## MCP Tools Used
- `mcp_mlflow_<tool1>` — <why>
- `mcp_mlflow_<tool2>` — <why>

## Steps
1. <Step one>
2. <Step two>
...

## Output Format
<What the skill returns to the user.>

## Constraints
- <Guardrail or limitation>
```

---

## CI/CD Quality Gate

For CI/CD integration, use `mlflow.genai.evaluate()` directly in your pipeline
script. MLflow AI Gateway (built into the MLflow Tracking Server) provides governed
LLM access, automatic tracing, and cost tracking — no custom gateway service needed.

---

## Test Commands

```bash
# Set up local dev environment
make dev-setup

# Unit tests (fast, no MLflow needed)
make test-unit

# Integration tests (requires local MLflow)
make mlflow-start
make seed-data
make test-integration
make mlflow-stop

# All tests
make test

# MCP contract check (requires cluster access)
make check-mcp
```

---

## Files to Understand Before Modifying

| File | Why it matters |
|------|---------------|
| `agent-lens/soul.md` | Defines Agent Lens identity, MCP tool allowlist, scoring rules, and intent routing. Changes here affect all conversations. |
| `agent-lens/config.yaml` | MCP endpoint URL and tool allowlist. Adding a tool here is a contract change. |
| `docs/product/identity.md` | Strategic boundary: what Agent Lens builds vs. consumes from MLflow. |
| `DESIGN.md` | Six design principles — read before proposing architecture changes. |
| `docs/product/mlflow-capability-audit.md` | Build vs. consume decisions for every feature area. |

---

## Common Mistakes to Avoid

| Mistake | Why it fails | What to do instead |
|---------|-------------|-------------------|
| `import mlflow` in a skill | MLflow SDK is not in the sandbox | Use `mcp_mlflow_*` tools |
| Custom scoring function | Duplicates MLflow's 20+ built-in judges | Use existing scorers via `evaluate_traces` |
| Hardcoded scorer list | List changes with MLflow versions | Use `list_scorers` to discover at runtime |
| Custom model registry DB | Duplicates LoggedModel | Use `search_logged_models` + tags |
| Direct MLflow REST call | Bypasses MCP trust boundary | Route through MLflow MCP |
| Rating on a /5 scale | No such scale exists | Report pass rates (% yes) |
| `pip install` in startup | Container image is immutable | Add to Containerfile build stage |

---

## Quick Reference

- **Design philosophy:** [DESIGN.md](DESIGN.md)
- **Security model:** [SECURITY.md](SECURITY.md)
- **Contributing guide:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Architecture:** [docs/architecture.md](docs/architecture.md)
- **Roadmap:** [docs/product/roadmap.md](docs/product/roadmap.md)
