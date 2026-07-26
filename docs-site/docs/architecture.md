---
sidebar_position: 4
title: Architecture
---

# Architecture

## System Overview

```mermaid
%%{init: {'theme': 'neutral'}}%%
graph TB
    subgraph Users
        PE[Platform Engineer]
        DEV[Agent Developer]
        CICD[CI/CD Pipeline]
    end
    
    subgraph AgentLens["Agent Lens (OpenShell Sandbox)"]
        Harness[Agent Harness]
        Soul[soul.md]
        Skills[16 Skills]
        Config[config.yaml]
    end
    
    subgraph MCP["MCP Layer"]
        MLflowMCP[MLflow MCP Server]
    end
    
    subgraph Data["Data Plane"]
        MLflow[(MLflow Tracking)]
        Traces[Agent Traces]
        Evals[Evaluation Runs]
    end
    
    PE -->|chat| Harness
    DEV -->|chat| Harness
    CICD -->|mlflow.genai.evaluate| MLflow
    
    Harness --> Soul
    Harness --> Skills
    Harness --> Config
    Harness -->|MCP tools| MLflowMCP
    
    MLflowMCP --> MLflow
    MLflow --> Traces
    MLflow --> Evals
```

## Design Principles

1. **MCP-native** — All data access through official MLflow MCP tools. No direct SDK calls at runtime.
2. **Skills as prompts** — Each skill is a SKILL.md file, not code. The LLM interprets it and calls MCP tools.
3. **Upstream-first** — Never fork MLflow MCP. Missing features go upstream.
4. **Conversational-first** — The UI is chat. Structured output (tables, reports) rendered in conversation.

## Component Details

### Agent Harness (runtime)

Agent Lens requires an MCP-capable agent harness — any runtime that can:
- Call MCP tools (streamable HTTP or stdio transport)
- Load and interpret SKILL.md prompt documents
- Maintain session context across multi-step workflows
- Provide a chat interface (web dashboard or CLI)

The reference implementation ships with **Hermes v0.19**, which provides all of the above plus a built-in web dashboard with auth. However, the skills, soul, and config are portable — see [Agent harness runtime](https://github.com/rrbanda/agentlens#agent-harness-runtime) for how to use a different harness.

### Agents being evaluated (target agents)

Agent Lens evaluates **any agent that sends traces to MLflow**, regardless of framework:

| Framework | MLflow integration |
|-----------|-------------------|
| LangGraph | `mlflow.langchain.autolog()` |
| Google ADK | `mlflow.tracing.enable()` or ADK's built-in tracing |
| LangChain | `mlflow.langchain.autolog()` |
| CrewAI | `mlflow.crewai.autolog()` |
| OpenAI Agents SDK | `mlflow.openai.autolog()` |
| AutoGen | `mlflow.autogen.autolog()` |
| LlamaIndex | `mlflow.llama_index.autolog()` |
| Custom | `@mlflow.trace` decorator or REST API |

### MLflow MCP Server

Official `mlflow mcp run` providing 19 tools:

```yaml
tools:
  include:
    # Observability
    - search_experiments
    - get_experiment
    - search_traces
    - get_trace
    - list_runs
    - describe_run
    # Evaluation
    - evaluate_traces
    - list_scorers
    # Annotation
    - log_trace_feedback
    - log_trace_expectation
    - set_trace_tag
    - delete_trace_tag
    # Assessment
    - get_trace_assessment
    - update_trace_assessment
    - delete_trace_assessment
    # Scorer management
    - register_llm_judge_scorer
    # Run-trace association
    - link_traces_to_run
    # Lifecycle
    - delete_traces
    - create_run
    - create_experiment
```

### MLflow AI Gateway (built into MLflow)

MLflow AI Gateway runs as part of the MLflow Tracking Server and provides:
- Governed LLM access for all providers (OpenAI, Anthropic, Gemini, etc.)
- Automatic tracing of all LLM requests with token counts
- Automatic evaluation — LLM judges run as traces arrive
- RBAC and credential management

No custom gateway service needed — Agent Lens consumes these features directly.

## Deployment Topology

```mermaid
%%{init: {'theme': 'neutral'}}%%
graph LR
    subgraph Kubernetes
        subgraph agent-ns["agent-lens namespace"]
            Sandbox[Agent Lens Sandbox Pod]
            Dashboard[Dashboard Route :9119]
        end
        subgraph mlflow-ns["mlflow namespace"]
            MCP[MLflow MCP Deploy]
            MLflow[MLflow Server]
        end
    end
    
    Sandbox -->|HTTP /mcp| MCP
    MCP -->|HTTPS + SA token| MLflow
    Dashboard -->|edge TLS| Sandbox
```

## ADRs

- [ADR-001: LoggedModel MCP Gap](/docs/adr/loggedmodel-gap) — Why LoggedModel operations are not yet available via MCP
