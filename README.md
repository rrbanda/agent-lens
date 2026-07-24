# Agent Lens

**AI agent evaluation platform for platform teams.** Evaluate, annotate, and gate agents you didn't build — powered by MLflow and the Model Context Protocol.

---

## The Problem

Platform teams manage fleets of AI agents they did not build. They need to:

1. **Score** whether agents perform well (not just see what they did)
2. **Annotate** production traces when quality drops
3. **Gate** deployments — agents should not ship if they regress
4. **Close the loop** — today's failure becomes tomorrow's test case

Agent Lens orchestrates this entire cycle through a conversational interface backed by MLflow's evaluation APIs.

## How It Works

```mermaid
%%{init: {'theme': 'neutral'}}%%
graph LR
    User[Platform Engineer] -->|natural language| AL[Agent Lens]
    AL -->|MCP| MCP[MCP Server]
    MCP -->|SDK| MLflow[(MLflow)]
    MLflow -->|traces| Agents[Your Agents]
```

```
Platform Team: "Evaluate the outreach agent"

Agent Lens:   Runs mlflow.genai.evaluate() with ToolCallCorrectness + RelevanceToQuery
              on 50 production traces...

              Quality Certification Report:
              ┌────────────────┬───────┬────────┐
              │ Dimension      │ Score │ Rating │
              ├────────────────┼───────┼────────┤
              │ Relevance      │ 4.2/5 │ PASS   │
              │ Tool Correct.  │ 3.1/5 │ FAIL   │
              └────────────────┴───────┴────────┘

              CERTIFICATION: NOT CERTIFIED
              Finding: Tool calls failing on date parsing (8/50 traces)
              Recommendation: Add to regression dataset and block deploy
```

## Key Features

| Feature | What It Does | MLflow API Used |
|---------|-------------|-----------------|
| **Evaluate** | Run scorers on agent traces | `mlflow.genai.evaluate()` |
| **Annotate** | Log human feedback on traces | `mlflow.log_feedback()` |
| **Set Expectations** | Define ground truth | `mlflow.log_expectation()` |
| **Create Test Cases** | Failure → regression dataset | `dataset.merge_records()` |
| **Quality Gate** | PASS/FAIL for CI/CD | Compare runs + thresholds |
| **Review Queue** | Surface traces needing attention | Smart trace sampling |
| **Scorer Profiles** | Pre-configured per agent type | Built-in + `make_judge()` |

## Architecture

```mermaid
%%{init: {'theme': 'neutral'}}%%
graph TB
    subgraph cluster[OpenShift Cluster]
        subgraph ns_al[agent-lens namespace]
            Agent[Agent Lens<br/><i>Hermes + Skills</i>]
        end

        subgraph ns_rhoai[redhat-ods-applications]
            MCP[MCP Server<br/><i>FastMCP + MLflow SDK</i>]
            MLflow[MLflow Tracking<br/><i>RHOAI Operator</i>]
        end

        subgraph ns_target[target-agent namespace]
            Target[Your Agent<br/><i>+ mlflow autolog</i>]
        end
    end

    User((Platform<br/>Engineer)) -->|HTTPS| Agent
    Agent -->|MCP over HTTP| MCP
    MCP -->|MLflow SDK + TLS| MLflow
    Target -->|traces| MLflow
```

### Components

| Component | Purpose |
|-----------|---------|
| **MCP Server** | MLflow SDK-based tools (evaluate, annotate, gate) |
| **Agent Lens** | Conversational evaluation agent (Hermes-based) |
| **Instrumentation** | Zero-code tracing for target agents |
| **mlflow/skills** | Vendored evaluation patterns and methodology |

## The AgentOps Loop

```mermaid
%%{init: {'theme': 'neutral'}}%%
graph LR
    O[Observe] --> E[Evaluate]
    E --> A[Annotate]
    A --> G[Gate]
    G --> I[Improve]
    I --> O
```

| Phase | Action | Tool |
|-------|--------|------|
| **Observe** | Agents generate traces via autolog | `search_traces` |
| **Evaluate** | Run scorers on production traces | `run_evaluation` |
| **Annotate** | Human feedback on flagged traces | `annotate_trace` |
| **Gate** | PASS/FAIL for deployment readiness | `check_quality_gate` |
| **Improve** | Failures become regression tests | `create_test_case` |

## Quick Start

### Prerequisites

- OpenShift cluster with RHOAI and MLflow operator
- `oc` CLI logged in
- Gemini API key (or other LLM provider)

### Deploy

```bash
git clone https://github.com/rrbanda/agent-lens.git && cd agent-lens
cp .env.example .env  # Edit with your values
make deploy-all
```

### Instrument an Agent

```bash
cp instrumentation/usercustomize.py $(python -m site --user-site)/
export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
export MLFLOW_EXPERIMENT_NAME="my-agent"
```

### Run Your First Evaluation

In the Agent Lens dashboard:
```
You:    "Evaluate the outreach agent using the tool-calling profile"
Agent:  [Runs evaluation, returns Quality Certification Report]
```

## Scorer Profiles

Pre-configured evaluation dimensions per agent type:

| Profile | Scorers | Best For |
|---------|---------|----------|
| **RAG Agent** | RelevanceToQuery + RetrievalGroundedness | Agents that retrieve documents |
| **Tool-Calling** | ToolCallCorrectness + ToolCallEfficiency + Relevance | Agents that call APIs/tools |
| **Chat Agent** | RelevanceToQuery + Guidelines (helpful, harmless) | Conversational assistants |

## Project Structure

```
agent-lens/
├── mcp-server/              # MLflow SDK-based evaluation tools
│   ├── entrypoint.py        # evaluate, annotate, gate, datasets
│   ├── Containerfile        # Production container build
│   ├── requirements.txt     # Python dependencies
│   └── deploy/              # Kubernetes manifests + NetworkPolicy
├── analyst-agent/           # Agent Lens (Hermes + skills)
│   ├── soul.md              # v2: evaluation platform identity
│   ├── skills/
│   │   ├── evaluate-agent/  # Quality Certification Reports
│   │   ├── review-trace/    # Human annotation workflow
│   │   ├── create-regression/ # Failure-to-dataset pipeline
│   │   ├── trace-explorer/  # Trace search and analysis
│   │   └── quality-dashboard/ # Fleet health overview
│   └── deploy/              # Kubernetes manifests + NetworkPolicy
├── instrumentation/         # Target agent auto-tracing
├── tests/                   # Unit + skill alignment tests
├── vendor/mlflow-skills/    # Upstream patterns (submodule)
├── docs/                    # Architecture + demo script
├── Makefile                 # make deploy-all, make eval
└── .env.example             # Configuration template
```

## Built On

- [MLflow GenAI Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/) — `evaluate()`, `log_feedback()`, datasets, scorers
- [mlflow/skills](https://github.com/mlflow/skills) — Agent evaluation patterns and methodology
- [Model Context Protocol](https://modelcontextprotocol.io/) — Tool integration standard
- [Hermes Agent](https://github.com/hermes-ai/hermes-agent) — Multi-skill agent framework

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

## License

Apache License 2.0 — see [LICENSE](LICENSE).
