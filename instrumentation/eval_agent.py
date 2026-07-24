"""
Agent Lens — Agent Evaluation Script

Evaluates an agent's output quality by:
1. Sending test prompts to the agent's API
2. Recording responses as an MLflow run
3. Running MLflow GenAI evaluation scorers (relevance, faithfulness, correctness)
4. Logging aggregate scores back to MLflow

Usage:
    export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
    export AGENT_API_URL="http://your-agent:8642"
    export AGENT_API_KEY="your-key"
    python eval_agent.py --experiment-name "my-agent" --workspace "my-namespace"

Requires: mlflow>=2.15.0, httpx
"""

import argparse
import json
import os
import sys
from datetime import datetime

import httpx

# Evaluation prompts — customize for your agent's domain
DEFAULT_EVAL_PROMPTS = [
    {
        "prompt": "Summarize the key benefits of our platform for enterprise customers.",
        "context": "Focus on scalability, security, and time-to-value.",
    },
    {
        "prompt": "Draft a follow-up email for a prospect who attended our demo last week.",
        "context": "The prospect showed interest in AI/ML capabilities.",
    },
    {
        "prompt": "What are the main competitive differentiators we should highlight?",
        "context": "Compared to open-source alternatives without enterprise support.",
    },
]


def call_agent(api_url: str, api_key: str, prompt: str) -> str:
    """Send a prompt to the agent and return the response."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "messages": [{"role": "user", "content": prompt}],
        "model": "default",
    }
    resp = httpx.post(
        f"{api_url}/v1/chat/completions",
        json=body,
        headers=headers,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def run_evaluation(
    experiment_name: str,
    workspace: str,
    agent_api_url: str,
    agent_api_key: str,
    prompts: list,
):
    """Run full evaluation pipeline."""
    import mlflow

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        print("ERROR: MLFLOW_TRACKING_URI not set", file=sys.stderr)
        sys.exit(1)

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    print(f"Running evaluation: {len(prompts)} prompts against {agent_api_url}")
    print(f"MLflow experiment: {experiment_name} (workspace: {workspace})")

    eval_data = []
    for i, item in enumerate(prompts, 1):
        prompt = item["prompt"]
        context = item.get("context", "")
        print(f"  [{i}/{len(prompts)}] {prompt[:60]}...")
        try:
            response = call_agent(agent_api_url, agent_api_key, prompt)
            eval_data.append({
                "inputs": prompt,
                "context": context,
                "outputs": response,
            })
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            eval_data.append({
                "inputs": prompt,
                "context": context,
                "outputs": f"ERROR: {e}",
            })

    if not eval_data:
        print("No successful responses to evaluate", file=sys.stderr)
        sys.exit(1)

    import pandas as pd

    eval_df = pd.DataFrame(eval_data)

    run_name = f"eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"\nStarting MLflow evaluation run: {run_name}")

    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("agent_url", agent_api_url)
        mlflow.log_param("num_prompts", len(prompts))
        mlflow.log_param("timestamp", datetime.now().isoformat())
        mlflow.log_param("workspace", workspace)

        try:
            from mlflow.metrics.genai import (
                relevance,
                faithfulness,
            )

            results = mlflow.evaluate(
                data=eval_df,
                model_type="question-answering",
                predictions="outputs",
                targets="context",
                extra_metrics=[relevance(), faithfulness()],
            )
            print(f"\n=== Results ===")
            print(results.metrics)
        except ImportError:
            print("MLflow GenAI metrics not available, logging raw scores")
            mlflow.log_metric("num_responses", len(eval_data))
            mlflow.log_metric("error_rate", sum(1 for d in eval_data if "ERROR" in d["outputs"]) / len(eval_data))

    print(f"\nEvaluation complete. View results in MLflow UI.")


def main():
    parser = argparse.ArgumentParser(description="Evaluate an AI agent using MLflow")
    parser.add_argument("--experiment-name", required=True, help="MLflow experiment name")
    parser.add_argument("--workspace", default="default", help="MLflow workspace (k8s namespace)")
    parser.add_argument("--prompts-file", help="JSON file with custom eval prompts")
    args = parser.parse_args()

    agent_api_url = os.environ.get("AGENT_API_URL")
    agent_api_key = os.environ.get("AGENT_API_KEY")

    if not agent_api_url or not agent_api_key:
        print("ERROR: Set AGENT_API_URL and AGENT_API_KEY environment variables", file=sys.stderr)
        sys.exit(1)

    prompts = DEFAULT_EVAL_PROMPTS
    if args.prompts_file:
        with open(args.prompts_file) as f:
            prompts = json.load(f)

    run_evaluation(
        experiment_name=args.experiment_name,
        workspace=args.workspace,
        agent_api_url=agent_api_url,
        agent_api_key=agent_api_key,
        prompts=prompts,
    )


if __name__ == "__main__":
    main()
