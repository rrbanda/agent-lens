# 🔍 Agent Lens

**AI-native observability for agentic systems.** Ask questions about your agents in natural language — get answers backed by MLflow traces, metrics, and evaluation data.

<p align="center">
  <img src="docs/images/architecture-overview.png" alt="Agent Lens Architecture" width="800"/>
</p>

---

## What Is Agent Lens?

Agent Lens is an **observability agent** — an AI that watches other AIs. It connects to MLflow via the Model Context Protocol (MCP) and provides a conversational interface for platform teams to understand how their AI agents are performing.

```
You:     "How is the outreach agent doing today?"
Agent:   "3 errors in the last hour (12% error rate, up from 2%).
          Root cause: RAG retrieval timeouts after the 2pm deployment.
          Recommendation: Check vector DB connection pool limits."
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Trace Explorer** | Search and summarize agent traces — latency, tokens, errors |
| **Eval Reports** | Pull quality scores (relevance, faithfulness, correctness) |
| **Run Comparison** | Before/after analysis across agent versions |
| **Failure Diagnosis** | Root-cause analysis using trace timelines |
| **Fleet Dashboard** | Health overview across all tracked agents |
| **Zero-Code Instrumentation** | Drop-in autologging for any OpenAI-compatible agent |

## Architecture

### Data Flow

<p align="center">
  <img src="docs/images/data-flow.png" alt="Agent Lens Data Flow" width="800"/>
</p>

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **MLflow MCP Server** | Exposes MLflow data as MCP tools | `mcp-server/` |
| **Agent Lens** (Hermes) | Conversational observability agent | `analyst-agent/` |
| **Instrumentation** | Auto-logging + evaluation scripts | `instrumentation/` |

### Hybrid MCP Pattern

Agent Lens uses a **production-grade hybrid pattern** — native MCP tool calls for simple queries, code execution with the `mcp` SDK for complex multi-step analysis:

<p align="center">
  <img src="docs/images/hybrid-pattern.png" alt="Hybrid MCP Pattern" width="700"/>
</p>

| Pattern | When | Example |
|---------|------|---------|
| **Native MCP** | Single tool call | "List experiments" → `mcp_mlflow_list_experiments` |
| **Code Execution** | Aggregation, loops, stats | "Error rate this week" → fetch 200 traces, compute % |

## Quick Start

### Prerequisites

- OpenShift cluster with [RHOAI](https://www.redhat.com/en/technologies/cloud-computing/openshift/openshift-ai) and MLflow operator
- `oc` CLI logged into the cluster
- Gemini API key (or other supported LLM provider)

### Deploy in 3 Steps

```bash
# 1. Clone
git clone https://github.com/rrbanda/agent-lens.git && cd agent-lens

# 2. Configure
cp .env.example .env
# Edit .env with your values

# 3. Deploy
make deploy-all
```

The dashboard URL is printed at the end. Login with `admin` / `openshift` (default).

### Instrument Your Agent

Add zero-code tracing to any Python agent:

```bash
cp instrumentation/usercustomize.py $(python -m site --user-site)/
export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
export MLFLOW_EXPERIMENT_NAME="my-agent"
```

Every LLM call is now captured as an MLflow trace — visible through Agent Lens.

## Project Structure

```
agent-lens/
├── mcp-server/              # MLflow MCP Server
│   ├── entrypoint.py        # Server implementation (FastMCP + httpx)
│   ├── Containerfile        # Container build
│   ├── requirements.txt
│   └── deploy/              # Kubernetes manifests
├── analyst-agent/           # Agent Lens (Hermes-based)
│   ├── config.yaml          # Hermes configuration
│   ├── soul.md              # Agent personality & instructions
│   ├── skills/              # Analytical skills (5 built-in)
│   └── deploy/              # Kubernetes manifests
├── instrumentation/         # Target agent instrumentation
│   ├── usercustomize.py     # Zero-code MLflow autologging
│   └── eval_agent.py        # Evaluation runner
├── docs/                    # Architecture & demo documentation
├── Makefile                 # Deployment automation
└── .env.example             # Configuration template
```

## MCP Tools Available

| Tool | Description |
|------|-------------|
| `list_experiments` | List all MLflow experiments |
| `get_experiment` | Get experiment details |
| `search_runs` | Search runs with filters |
| `get_run` | Full run details (metrics, params, tags) |
| `get_metric_history` | Metric values over time |
| `compare_runs` | Side-by-side run comparison |
| `search_traces` | Search agent traces |
| `set_trace_tag` | Tag traces for tracking |
| `log_feedback` | Log evaluation scores |
| `health_check` | Server connectivity check |

## Example Queries

| Question | Skill Used | Output |
|----------|-----------|--------|
| "Show me the last 10 traces" | trace-explorer | Table with status, latency, tokens |
| "What's the agent's quality score?" | eval-report | Relevance/faithfulness/correctness |
| "Compare before and after the prompt change" | compare-agents | Delta table with winner |
| "Why did trace X fail?" | diagnose-failure | Root cause + remediation |
| "How are all our agents doing?" | quality-dashboard | Fleet health overview |

## Configuration

### LLM Providers

Agent Lens defaults to Gemini but supports any LLM provider compatible with Hermes:

```yaml
# config.yaml
model:
  default: "gemini-2.5-flash"
  provider: gemini       # or: openai, anthropic, custom
```

### MCP Server Connection

```yaml
mcp_servers:
  mlflow:
    url: "http://mlflow-mcp-server:8080/mcp"
    timeout: 180
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

## Related Projects

- [MLflow](https://mlflow.org/) — ML experiment tracking and model registry
- [Model Context Protocol](https://modelcontextprotocol.io/) — Open standard for AI tool integration
- [Hermes Agent](https://github.com/hermes-ai/hermes-agent) — Multi-skill AI agent framework
- [RHOAI](https://www.redhat.com/en/technologies/cloud-computing/openshift/openshift-ai) — Red Hat OpenShift AI platform
