---
sidebar_position: 1
title: "ADR-001: LoggedModel MCP Gap"
---

# ADR-001: LoggedModel Operations Require Gateway MCP

## Status

Accepted (July 2026)

## Context

The official MLflow MCP server (`mlflow mcp run` in MLflow 3.14) does not expose LoggedModel CRUD operations. The full MLflow Python SDK supports:

- `mlflow.register_logged_model()`
- `mlflow.set_logged_model_tag()`
- `mlflow.search_logged_models()`
- `mlflow.get_logged_model()`

But none of these are available as MCP tools.

## Decision

Agent Lens skills that need LoggedModel data (agent-registry, compliance-export, audit-trail) will:

1. **Today:** Derive agent identity from experiments and evaluation run tags
2. **M2:** Use the Agent Lens Gateway MCP which bridges the SDK gap

The Gateway will expose:
- `search_agents` (wraps `search_logged_models`)
- `get_agent_status` (wraps `get_logged_model` + tags)
- `qualify_agent` (wraps `set_logged_model_tag` + audit)

## Consequences

- No full agent registry until Gateway ships (M2)
- Skills document this limitation explicitly
- Integration tests validate only official MCP tools
- Gateway becomes the single point for SDK-bridging, not scattered workarounds
