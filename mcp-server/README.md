# Agent Lens — MLflow Evaluation MCP Server (v2)

A [Model Context Protocol](https://modelcontextprotocol.io/) server that provides AI agents
with **evaluation, annotation, and governance** capabilities over MLflow data.

Built on the MLflow Python SDK (not raw REST), enabling `mlflow.genai.evaluate()`,
`mlflow.log_feedback()`, and dataset management directly as MCP tools.

## Tool Categories

### Observability (read)
| Tool | Description |
|------|-------------|
| `list_experiments` | List all MLflow experiments |
| `search_traces` | Search traces with filters |
| `get_trace` | Full trace details with spans and assessments |
| `search_runs` | Search evaluation/training runs |

### Evaluation (the core)
| Tool | Description |
|------|-------------|
| `run_evaluation` | Run `mlflow.genai.evaluate()` with selected scorers on traces or datasets |
| `list_scorers` | Show available built-in and registered scorers |

### Annotation (human feedback loop)
| Tool | Description |
|------|-------------|
| `annotate_trace` | Log human feedback via `mlflow.log_feedback()` |
| `set_expectation` | Set ground truth via `mlflow.log_expectation()` |

### Datasets (regression tests)
| Tool | Description |
|------|-------------|
| `list_datasets` | Show available evaluation datasets |
| `create_test_case` | Convert a production trace into a regression test case |

### Governance (deployment gates)
| Tool | Description |
|------|-------------|
| `check_quality_gate` | Compare against thresholds/baseline, return PASS/FAIL for CI/CD |
| `get_review_queue` | Smart sampling of traces needing human review |

### System
| Tool | Description |
|------|-------------|
| `health_check` | Connectivity and configuration check |

## Architecture

```
Platform Team --chat--> Agent Lens --MCP--> This Server --SDK--> MLflow
                                                          |
                                                          +--> mlflow.genai.evaluate()
                                                          +--> mlflow.log_feedback()
                                                          +--> mlflow.genai.datasets
```

## Quick Start

```bash
export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
export JUDGE_MODEL="gemini:/gemini-2.5-flash"

pip install -r requirements.txt
python entrypoint.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | (required) | MLflow server URL |
| `MLFLOW_EXPERIMENT_ID` | (optional) | Default experiment |
| `JUDGE_MODEL` | `gemini:/gemini-2.5-flash` | LLM for scorers |
| `MCP_HOST` | `0.0.0.0` | Bind address |
| `MCP_PORT` | `8080` | Bind port |

## Based On

- [MLflow GenAI Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/)
- [mlflow/skills](https://github.com/mlflow/skills) — agent-evaluation patterns
- [MLflow Human Feedback](https://mlflow.org/docs/latest/genai/assessments/feedback.md)
