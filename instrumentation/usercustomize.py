"""
Agent Lens — MLflow Auto-Instrumentation

Drop this file into the target agent's Python environment as usercustomize.py
to automatically capture all OpenAI-compatible API calls into MLflow traces.

How it works:
  - Python loads usercustomize.py automatically from site-packages on startup
  - We import mlflow and enable autologging for openai-compatible providers
  - Every LLM call made by the agent is captured as a trace in MLflow

Environment Variables Required:
    MLFLOW_TRACKING_URI: MLflow server URL
    MLFLOW_EXPERIMENT_NAME: Experiment name (creates if not exists)

Optional:
    MLFLOW_WORKSPACE: Target workspace/namespace (default: "default")
"""

import os
import sys


def _setup_mlflow_autolog():
    """Configure MLflow OpenAI autologging if environment is set."""
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME")

    if not tracking_uri or not experiment_name:
        return

    try:
        import mlflow

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        mlflow.openai.autolog(
            log_models=False,
            log_input_examples=True,
        )
        print(
            f"[agent-lens] MLflow autolog active: "
            f"uri={tracking_uri}, experiment={experiment_name}",
            file=sys.stderr,
        )
    except ImportError:
        print("[agent-lens] mlflow not installed, skipping autolog", file=sys.stderr)
    except Exception as e:
        print(f"[agent-lens] MLflow autolog failed: {e}", file=sys.stderr)


_setup_mlflow_autolog()
