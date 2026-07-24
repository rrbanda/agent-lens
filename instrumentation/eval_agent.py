"""
Agent Lens — offline CLI evaluation helper (target-agent side).

Calls an OpenAI-compatible agent API, then scores responses with
`mlflow.genai.evaluate` and built-in GenAI scorers (yes/no pass rates).

This script runs **outside** Hermes (has tracking credentials). Hermes must
never `import mlflow` in its sandbox — use official MCP instead.

Usage:
    export MLFLOW_TRACKING_URI="https://your-mlflow:8443"
    export AGENT_API_URL="http://your-agent:8642"
    export AGENT_API_KEY="your-key"
    python eval_agent.py --experiment-name "my-agent"

Requires: mlflow>=3.8, httpx, pandas
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import httpx

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
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "messages": [{"role": "user", "content": prompt}],
        "model": "default",
    }
    resp = httpx.post(
        f"{api_url.rstrip('/')}/v1/chat/completions",
        json=body,
        headers=headers,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _build_scorers(profile: str):
    from mlflow.genai.scorers import (
        Guidelines,
        RelevanceToQuery,
        RetrievalGroundedness,
        ToolCallCorrectness,
        ToolCallEfficiency,
    )

    profile = (profile or "chat").lower()
    if profile == "rag":
        return [RelevanceToQuery(), RetrievalGroundedness()]
    if profile in ("tool", "tool-calling", "tool_calling"):
        return [ToolCallCorrectness(), ToolCallEfficiency(), RelevanceToQuery()]
    if profile == "chat":
        return [
            RelevanceToQuery(),
            Guidelines(
                name="helpful_harmless_honest",
                guidelines="Response is helpful, harmless, and honest.",
            ),
        ]
    raise SystemExit(f"Unknown profile: {profile}. Use rag|tool-calling|chat")


def run_evaluation(
    experiment_name: str,
    workspace: str,
    agent_api_url: str,
    agent_api_key: str,
    prompts: list,
    profile: str,
):
    import mlflow
    import pandas as pd
    from mlflow.genai import evaluate

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        print("ERROR: MLFLOW_TRACKING_URI not set", file=sys.stderr)
        sys.exit(1)

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    print(f"Running evaluation: {len(prompts)} prompts against {agent_api_url}")
    print(f"MLflow experiment: {experiment_name} (workspace: {workspace})")
    print(f"Profile: {profile}")

    eval_data = []
    for i, item in enumerate(prompts, 1):
        prompt = item["prompt"]
        context = item.get("context", "")
        print(f"  [{i}/{len(prompts)}] {prompt[:60]}...")
        try:
            response = call_agent(agent_api_url, agent_api_key, prompt)
            row = {
                "inputs": {"question": prompt},
                "outputs": response,
            }
            if context:
                row["expectations"] = {"context": context}
            eval_data.append(row)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            eval_data.append(
                {
                    "inputs": {"question": prompt},
                    "outputs": f"ERROR: {e}",
                }
            )

    if not eval_data:
        print("No responses to evaluate", file=sys.stderr)
        sys.exit(1)

    scorers = _build_scorers(profile)
    run_name = f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    print(f"\nStarting mlflow.genai.evaluate run: {run_name}")

    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("agent_url", agent_api_url)
        mlflow.log_param("num_prompts", len(prompts))
        mlflow.log_param("profile", profile)
        mlflow.log_param("workspace", workspace)
        mlflow.log_param("timestamp", datetime.now(timezone.utc).isoformat())

        results = evaluate(
            data=pd.DataFrame(eval_data),
            scorers=scorers,
        )
        print("\n=== Metrics (pass-oriented GenAI scorers) ===")
        metrics = getattr(results, "metrics", None) or results
        print(metrics)

    print("\nEvaluation complete. View results in MLflow UI.")
    print("Note: RetrievalGroundedness needs retriever spans — may be N/A for chat-only agents.")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate an AI agent with mlflow.genai.evaluate"
    )
    parser.add_argument("--experiment-name", required=True)
    parser.add_argument("--workspace", default="default")
    parser.add_argument("--prompts-file", help="JSON file with custom eval prompts")
    parser.add_argument(
        "--profile",
        default="chat",
        choices=["rag", "tool-calling", "chat"],
        help="Scorer profile",
    )
    args = parser.parse_args()

    agent_api_url = os.environ.get("AGENT_API_URL")
    agent_api_key = os.environ.get("AGENT_API_KEY")
    if not agent_api_url or not agent_api_key:
        print("ERROR: Set AGENT_API_URL and AGENT_API_KEY", file=sys.stderr)
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
        profile=args.profile,
    )


if __name__ == "__main__":
    main()
