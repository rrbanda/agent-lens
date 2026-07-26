# ADR-001: LoggedModel MCP Gap — How Agent Lens Accesses LoggedModel Operations

**Status:** Proposed
**Date:** 2026-07-26
**Area:** MCP / Architecture
**Deciders:** Agent Lens maintainers

---

## Context

Agent Lens depends on 8 MLflow LoggedModel operations for its agent registry and qualification lifecycle:

| Operation | Used by |
|-----------|---------|
| `search_logged_models` | agent-registry, audit-trail, executive-summary, compliance-export, evaluate-agent |
| `get_logged_model` | agent-registry |
| `set_logged_model_tags` | evaluate-agent, agent-registry |
| `create_logged_model` | agent-registry |
| `create_external_model` | agent-registry |
| `finalize_logged_model` | evaluate-agent |
| `delete_logged_model_tag` | (lifecycle cleanup) |
| `log_logged_model_params` | agent-registry |

These tools are in `config.yaml` and referenced by 5 of 12 skills.

**The problem:** The official MLflow MCP server (`mlflow mcp run`, shipped with `mlflow[mcp]`) does NOT expose LoggedModel CRUD tools. The `models` MCP category wraps `mlflow models` CLI commands (build-docker, serve, predict) — model serving operations, not LoggedModel management. LoggedModel operations exist only in the Python SDK (`mlflow.search_logged_models()`, etc.) and the REST API.

This means all LoggedModel-dependent skills will fail when connecting to the official upstream MCP server.

## Options

### Option A: Community MCP Server (`us-all/mlflow-mcp-server`)

Use the community-maintained `us-all/mlflow-mcp-server` which exposes 82 tools including all 8 LoggedModel operations.

**Pros:**
- Immediately available, no custom code to maintain
- Covers LoggedModel, Model Registry, Prompts, Webhooks — broader surface than official
- Active community project

**Cons:**
- Not the official MLflow MCP server — potential compatibility drift
- Additional dependency to track and validate
- May not track upstream MLflow API changes as quickly
- Violates Agent Lens design principle of "upstream official MLflow MCP only"

### Option B: Gateway MCP Wrapper (Recommended)

The planned Agent Lens Gateway (M2 FastAPI service) already needs to expose audit/registry MCP tools (`log_audit_event`, `query_audit_trail`, `get_registry`, `register_agent`). Extend it to also proxy LoggedModel SDK calls as MCP tools.

**Pros:**
- Single additional MCP server (Gateway) instead of replacing the upstream server
- Agent Lens controls the surface area — expose only what skills need
- Gateway is already planned for M2; marginal cost to add LoggedModel proxy
- Keeps official MLflow MCP for traces/evaluation/annotation (majority of tools)
- Gateway can add value on top of raw SDK (e.g., compute EXPIRED status, aggregate qualification history)

**Cons:**
- Agent Lens must maintain the SDK wrapper code
- Adds latency (Gateway -> MLflow SDK -> MLflow Tracking Server)
- Must track MLflow SDK API changes across versions

### Option C: Upstream Contribution — LoggedModel CLI Commands

Contribute `mlflow logged-models` CLI commands to upstream MLflow. Once merged, `mlflow mcp run` would automatically expose them.

**Pros:**
- Solves the problem at the root — benefits entire MLflow ecosystem
- No custom wrapper to maintain long-term
- Aligns with Agent Lens principle of upstream-first

**Cons:**
- Uncertain timeline — depends on upstream review and acceptance
- Does not solve the immediate M2 need
- Requires maintaining a PR through the upstream process

## Decision

**Option B (Gateway MCP Wrapper)** for M2, with **Option C (Upstream Contribution)** as a parallel track.

Rationale:
1. The Gateway is already a planned M2 component — adding LoggedModel proxy is incremental
2. The dual-MCP topology (MLflow MCP for data plane, Gateway MCP for decision plane) is already the documented architecture in `identity.md`
3. If the upstream contribution (Option C) succeeds, the Gateway can drop its LoggedModel proxy and the skills can point at official MCP — a clean migration path
4. Option A is rejected because it replaces the official MCP entirely, violating the upstream-first principle

### Config topology after this decision

```yaml
mcp_servers:
  mlflow:
    url: "http://mlflow-mcp.../mcp"
    tools:
      include:
        # 16 official tools (traces, runs, experiments, scorers)
        - search_traces
        - get_trace
        - evaluate
        # ... etc
  agentlens:
    url: "http://agent-lens-gateway.../mcp"
    tools:
      include:
        # LoggedModel proxy (8 tools)
        - search_logged_models
        - get_logged_model
        - set_logged_model_tags
        # ... etc
        # Audit/Registry (4 tools)
        - log_audit_event
        - query_audit_trail
        - get_registry
        - register_agent
```

## Consequences

### Positive
- Skills work against official upstream MLflow MCP for 75%+ of operations
- LoggedModel gap is bridged without abandoning the upstream server
- Clean migration path when upstream adds LoggedModel CLI support
- Gateway MCP consolidates all "Agent Lens decision plane" tools in one server

### Negative
- Agent Lens must maintain LoggedModel SDK wrapper code in the Gateway
- Two MCP servers to configure and monitor instead of one
- `test_skill_alignment.py` must be updated to validate tools against both MCP servers

### Risks
- MLflow SDK API for LoggedModel may change between versions (mitigated by CI contract checks)
- Gateway MCP adds a hop for LoggedModel operations (mitigated by being in-cluster, low latency)

## Follow-up Actions

1. Move LoggedModel tools from `mlflow` MCP config section to `agentlens` section when Gateway is built
2. Open upstream MLflow issue/PR for `mlflow logged-models` CLI commands
3. Update `test_skill_alignment.py` to support dual-MCP validation
4. Update skills to use `mcp_agentlens_*` prefix for LoggedModel tools (after Gateway ships)
