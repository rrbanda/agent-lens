# Contributing to Agent Lens

Thank you for your interest in contributing to Agent Lens! This document provides guidelines and information for contributors.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.11+
- Access to an OpenShift cluster with RHOAI (for integration testing)
- `oc` CLI (for deployment testing)

### Development Setup

```bash
# Clone your fork
git clone https://github.com/<your-username>/agent-lens.git
cd agent-lens

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r mcp-server/requirements.txt
pip install pytest

# Run tests
pytest
```

### Running Tests

```bash
# All tests
pytest

# Skill alignment only (fast, no dependencies)
pytest tests/test_skill_alignment.py -v

# MCP tool unit tests
pytest tests/test_mcp_tools.py -v
```

## How to Contribute

### Reporting Bugs

Open a [GitHub Issue](https://github.com/rrbanda/agent-lens/issues/new) with:

1. **Summary** — one sentence describing the problem
2. **Environment** — OpenShift version, RHOAI version, Python version
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

### Adding a New Scorer

1. Add the scorer import and instantiation to `mcp-server/entrypoint.py` in the `scorer_map`
2. Update `list_scorers()` to document it
3. Add a test case in `tests/test_mcp_tools.py`
4. Update scorer profile documentation in the README

### Adding a New Skill

1. Create `analyst-agent/skills/<skill-name>/SKILL.md`
2. Reference only tools that exist in `entrypoint.py` (use `mcp_agent-lens_<tool>` format)
3. Add the skill to `analyst-agent/deploy/kustomization.yaml` configMapGenerator
4. Add the skill name to the `SKILLS` env var in `analyst-agent/deploy/deployment.yaml`
5. Run `pytest tests/test_skill_alignment.py` to verify

### Adding a New MCP Tool

1. Add the function to `mcp-server/entrypoint.py` with `@mcp.tool()` decorator
2. Include `@with_timeout()` and `@with_retry()` decorators
3. Use `_get_client()` for the MLflow client (singleton)
4. Add a test in `tests/test_mcp_tools.py`
5. Document the tool in `mcp-server/README.md`

### Adding a Deployment Target

1. Create `mcp-server/deploy/overlays/<target>/kustomization.yaml`
2. Override environment-specific values (tracking URI, image, resources)
3. Document in the README under "Getting Started"

## Style Guide

### Python

- Follow PEP 8
- Use type hints for function parameters
- Docstrings for all public functions (used as MCP tool descriptions)
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

Key decisions are documented in `docs/architecture.md`. When proposing changes that affect architecture, please reference or update that document.

## Release Process

Releases follow semantic versioning:
- **Patch** (0.1.x) — bug fixes, dependency updates
- **Minor** (0.x.0) — new tools, skills, features
- **Major** (x.0.0) — breaking changes to MCP tool interface

## Questions?

- Open a [Discussion](https://github.com/rrbanda/agent-lens/discussions) for questions
- Open an [Issue](https://github.com/rrbanda/agent-lens/issues) for bugs or feature requests
