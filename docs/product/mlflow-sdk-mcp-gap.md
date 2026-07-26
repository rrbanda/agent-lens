# MLflow SDK vs MCP Gap Analysis for Agent Lens

*Owner: Product Management / Architecture*
*Last updated: July 2026*
*Research basis: MLflow 3.x SDK, official `mlflow[mcp]` server, Agent Lens skills audit*

---

## Overview

The official MLflow MCP server (`mlflow mcp run`) wraps CLI commands from 6 categories as MCP tools. The MLflow Python SDK offers significantly more functionality. This document maps the delta and identifies which SDK-only capabilities matter for Agent Lens.

**Scope:** 47 official MCP tools vs 200+ SDK methods across 15 API areas.

---

## MCP Category Configuration

The `MLFLOW_MCP_TOOLS` environment variable controls which categories are exposed:

| Preset | Categories |
|--------|-----------|
| `genai` (default) | traces, scorers, experiments, runs |
| `ml` | experiments, runs, models, deployments |
| `all` | All 6 categories |

Agent Lens requires `genai` at minimum. LoggedModel operations are not in any category.

---

## Gap Matrix

| SDK API Area | SDK Methods | Official MCP Tools | Agent Lens Uses | Coverage | Agent Lens Value |
|-------------|-------------|-------------------|----------------|----------|-----------------|
| **Traces** | 15+ | 11 | 8 | Strong | Core |
| **Assessments** | 5 | 5 | 4 (+1 new) | Strong | Core |
| **Runs** | 25+ | 6 | 2 (+2 new) | Moderate | Important |
| **Experiments** | 15 | 8 | 2 (+1 new) | Moderate | Important |
| **Scorers** | 20+ | 2 (+1 new) | 2 (+1 new) | Moderate | Important |
| **LoggedModel** | 11 | 0 (SDK-only) | 8 (via Gateway) | None | **Critical** |
| **Prompts** | 8+ | 0 | 0 | None | **High** |
| **Eval Datasets** | 6+ | 0 | 0 | None | **High** |
| **Webhooks** | 6 | 0 | 0 | None | Medium |
| **Model Registry** | 20+ | some (ml) | 0 | None (AL) | Low |
| **Deployments** | 14 | 14 (ml) | 0 | None (AL) | Low |
| **Models (serving)** | 7 | 6 (ml) | 0 | None (AL) | Low |
| **Artifacts** | 10 | 1 (ml) | 0 | None (AL) | Low |
| **Labeling Sessions** | 8 | 0 | 0 | None | Medium (conditional) |
| **Workspaces** | 5 | 0 | 0 | None | Low-Medium |

---

## Critical Gap: LoggedModel (8 tools, 0 MCP)

See [ADR-001](../adr/001-loggedmodel-mcp-gap.md) for full analysis and decision.

Agent Lens uses 8 LoggedModel SDK operations that have no official MCP tool. These are critical for the agent-registry skill and qualification tagging in evaluate-agent. The decision is to proxy these through the Agent Lens Gateway MCP server.

| SDK Method | Agent Lens tool name | Skills using it |
|-----------|---------------------|----------------|
| `mlflow.search_logged_models()` | `search_logged_models` | agent-registry, audit-trail, executive-summary, compliance-export, evaluate-agent |
| `mlflow.get_logged_model()` | `get_logged_model` | agent-registry |
| `mlflow.set_logged_model_tags()` | `set_logged_model_tags` | evaluate-agent, agent-registry |
| `mlflow.initialize_logged_model()` | `create_logged_model` | agent-registry |
| `mlflow.create_external_model()` | `create_external_model` | agent-registry |
| `mlflow.finalize_logged_model()` | `finalize_logged_model` | evaluate-agent |
| `mlflow.delete_logged_model_tag()` | `delete_logged_model_tag` | (lifecycle cleanup) |
| `mlflow.log_model_params()` | `log_logged_model_params` | agent-registry |

---

## High-Value SDK-Only Capabilities

### 1. Prompts API (8+ methods, 0 MCP)

| SDK Method | What it does | Agent Lens use |
|-----------|-------------|----------------|
| `mlflow.genai.register_prompt()` | Register/version a prompt template | Track prompt versions per agent |
| `mlflow.genai.load_prompt()` | Load prompt by URI | Inspect current agent prompts |
| `mlflow.genai.search_prompts()` | Search prompts by name/tags | Prompt inventory for fleet |
| `mlflow.genai.set_prompt_alias()` | Set alias (e.g., "production") | Track which prompt is active |
| `mlflow.genai.optimize_prompts()` | Automated prompt optimization | Improve failing agents |

**Enables:** New `prompt-registry` skill (M3), prompt drift detection in `drift-detection` (M4)

### 2. Evaluation Datasets API (6+ methods, 0 MCP)

| SDK Method | What it does | Agent Lens use |
|-----------|-------------|----------------|
| `mlflow.genai.create_dataset()` | Create evaluation dataset | Durable regression suites |
| `EvaluationDataset.merge_records()` | Add records to dataset | Build golden datasets |
| `mlflow.genai.get_dataset()` | Retrieve dataset | Load for evaluation |
| `mlflow.genai.delete_dataset()` | Delete dataset | Lifecycle management |

**Enables:** Transforms `create-regression` from tag-based workaround to proper dataset management. Tracked as upstream need "Before M3" in roadmap.

### 3. Webhooks API (6 methods, 0 MCP)

| SDK Method | What it does | Agent Lens use |
|-----------|-------------|----------------|
| `client.create_webhook()` | Register event callback | Auto-evaluate on model version change |
| `client.list_webhooks()` | List active webhooks | Audit notification config |
| `client.test_webhook()` | Verify connectivity | Health checks |

**Events of interest:** `model_version.created`, `prompt.created`, `budget_policy.exceeded`

**Enables:** M3 `alert-config` skill for quality regression alerts.

---

## Official MCP Tools Agent Lens Now Uses

After the gap audit, Agent Lens allowlists 29 tools from the official MLflow MCP:

### Core (used since M1)

| Tool | Category | Primary skills |
|------|----------|---------------|
| `search_experiments` | experiments | evaluate-agent, quality-dashboard, executive-summary |
| `get_experiment` | experiments | evaluate-agent, trace-explorer |
| `search_traces` | traces | 10 skills |
| `get_trace` | traces | review-trace, analyze-session, trace-explorer |
| `evaluate` | scorers | evaluate-agent |
| `list_scorers` | scorers | evaluate-agent |
| `log_feedback` | traces | review-trace, create-regression |
| `log_expectation` | traces | review-trace, create-regression |
| `set_trace_tag` | traces | review-trace, create-regression |
| `list_runs` | runs | quality-dashboard, audit-trail, compare-evaluations |
| `describe_run` | runs | audit-trail, compare-evaluations, compliance-export |

### Added in M2 skills gap audit

| Tool | Category | Primary skills |
|------|----------|---------------|
| `delete_trace_tag` | traces | review-trace |
| `get_assessment` | traces | review-trace |
| `update_assessment` | traces | review-trace |

### Added in SDK gap audit (this document)

| Tool | Category | Primary skills |
|------|----------|---------------|
| `delete_assessment` | traces | review-trace |
| `register_llm_judge` | scorers | evaluate-agent |
| `link_traces` | runs | evaluate-agent, create-regression |
| `experiments_csv` | experiments | compliance-export |
| `delete_traces` | traces | (M4+ data retention) |
| `create_run` | runs | evaluate-agent (M3) |
| `create_experiment` | experiments | (M3 onboarding) |

### Via Gateway MCP (LoggedModel proxy)

| Tool | Category | Primary skills |
|------|----------|---------------|
| `search_logged_models` | LoggedModel | agent-registry, audit-trail, executive-summary, compliance-export, evaluate-agent |
| `get_logged_model` | LoggedModel | agent-registry |
| `set_logged_model_tags` | LoggedModel | evaluate-agent, agent-registry |
| `create_logged_model` | LoggedModel | agent-registry |
| `create_external_model` | LoggedModel | agent-registry |
| `finalize_logged_model` | LoggedModel | evaluate-agent |
| `delete_logged_model_tag` | LoggedModel | (lifecycle cleanup) |
| `log_logged_model_params` | LoggedModel | agent-registry |

---

## Per-Skill Impact

| Skill | Current tools | New tools from this audit | Gap remaining |
|-------|--------------|--------------------------|---------------|
| `evaluate-agent` | 7 | `register_llm_judge`, `link_traces` | None for M2 |
| `review-trace` | 8 | `delete_assessment` | Review queue (upstream need) |
| `create-regression` | 5 | `link_traces` | `create_evaluation_dataset` (upstream) |
| `compliance-export` | 4 | `experiments_csv` | PDF export (M4) |
| `agent-registry` | 7 | None | K8s auto-discovery (M3) |
| `audit-trail` | 4 | None | Gateway audit tools (M2) |
| `aggregate-traces` | 1 | None | Server-side aggregation (upstream) |
| `compare-evaluations` | 2 | None | None |
| `executive-summary` | 2 | None | Gateway registry tools (M2) |
| `quality-dashboard` | 3 | None | Fleet pagination (upstream) |
| `analyze-session` | 2 | None | Cross-experiment sessions (M4) |
| `trace-explorer` | 3 | None | None |

---

## Implementation Phases

### Phase 1: Immediate (done)

- Fixed 3 tool name mismatches across entire codebase
- Added 7 official MCP tools to allowlist
- Created ADR-001 for LoggedModel gap

### Phase 2: M2 — Bridge LoggedModel Gap

- Build Gateway MCP with LoggedModel proxy + audit/registry tools
- Move LoggedModel tools from `mlflow` to `agentlens` MCP config section
- Update skills to use `mcp_agentlens_*` prefix for LoggedModel tools
- Update tests for dual-MCP validation

### Phase 3: M3 — Leverage SDK-Only APIs via Gateway

| Capability | Gateway wrapper | New/enhanced skill |
|-----------|----------------|-------------------|
| Prompts | `prompt_register`, `prompt_search`, `prompt_load` | New `prompt-registry` skill |
| Eval Datasets | `create_evaluation_dataset`, `merge_dataset_records` | Enhanced `create-regression` |
| Webhooks | `create_webhook`, `list_webhooks` | New `alert-config` skill |
| Metric history | `get_metric_history` | New `trend-analysis` skill |

### Phase 4: Upstream Contributions (parallel track)

| Contribution | MLflow component | Blocks |
|-------------|-----------------|--------|
| LoggedModel CLI commands | `mlflow` CLI | Removes need for Gateway proxy |
| `create_evaluation_dataset` MCP tool | `mlflow mcp` | Removes `create-regression` workaround |
| Review queue / triage tool | `mlflow mcp` | Removes `review-trace` search workaround |
| Aggregate experiment statistics | `mlflow mcp` | Removes 20-experiment cap |

---

## Summary

| Category | Count |
|----------|-------|
| Official MCP tools (total) | 47 |
| Agent Lens uses (official MCP) | 21 |
| Agent Lens uses (via Gateway proxy) | 8 |
| Agent Lens total allowlisted | 29 |
| Tool name mismatches fixed | 3 |
| New official tools added to allowlist | 7 |
| SDK-only gaps with high Agent Lens value | 3 (Prompts, Datasets, Webhooks) |
| SDK-only gaps with medium value | 2 (Labeling Sessions, Workspaces) |
| Upstream contributions needed | 4 |
