"""Seed a local MLflow instance with realistic agent data for integration tests.

Creates 3 experiments with traces, assessments, tags, and evaluation runs
to simulate a real agent fleet that Agent Lens skills can query.

Usage:
    MLFLOW_TRACKING_URI=http://127.0.0.1:5555 python tests/seed_mlflow_data.py
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
import uuid

import mlflow
from mlflow.entities import SpanType
from mlflow.entities.assessment_source import AssessmentSource

TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5555")

EXPERIMENTS = [
    {"name": "customer-support-agent", "agent_type": "rag"},
    {"name": "code-review-agent", "agent_type": "tool-calling"},
    {"name": "sales-assistant-agent", "agent_type": "chat"},
]

SUPPORT_PROMPTS = [
    "How do I reset my password?",
    "What is your return policy?",
    "I need help with my order #12345",
    "Can you explain the billing charges?",
    "My account is locked, what should I do?",
    "How do I upgrade my subscription?",
    "Is there a discount for annual plans?",
    "Where can I find the API documentation?",
]

CODE_REVIEW_PROMPTS = [
    "Review this Python function for performance issues",
    "Check this SQL query for injection vulnerabilities",
    "Analyze this React component for accessibility problems",
    "Find potential memory leaks in this Go code",
    "Review error handling in this Java service",
    "Check this Dockerfile for security best practices",
]

SALES_PROMPTS = [
    "Draft a follow-up email for the enterprise demo",
    "What are our competitive differentiators vs Datadog?",
    "Prepare talking points for the security review meeting",
    "Summarize the key benefits for healthcare customers",
    "Generate a pricing comparison for the mid-tier plan",
    "Draft a proposal for the Q3 renewal",
]

RESPONSES = {
    "rag": [
        "Based on our documentation, you can reset your password by visiting Settings > Security > Change Password.",
        "Our return policy allows returns within 30 days of purchase with a valid receipt.",
        "I found your order #12345. It was shipped on June 15 and is currently in transit.",
        "Your billing shows a $29.99 monthly charge for the Pro plan plus $5.00 for additional storage.",
        "Your account was locked due to 5 failed login attempts. I've sent a reset link to your email.",
        "To upgrade, go to Account > Subscription > Upgrade Plan. I can walk you through the options.",
        "Yes! Annual plans receive a 20% discount. Your Pro plan would be $287.90/year instead of $359.88.",
        "API documentation is available at docs.example.com/api. The latest version is v3.2.",
    ],
    "tool-calling": [
        "I've analyzed the function. The nested loops on lines 15-23 have O(n^2) complexity. Consider using a dict lookup.",
        "CRITICAL: Line 42 uses string formatting for SQL. Use parameterized queries to prevent injection.",
        "Found 3 accessibility issues: missing alt text on images, no aria-labels on buttons, low color contrast.",
        "Potential leak on line 89: goroutine holds reference to large buffer after context cancellation.",
        "Error handling is incomplete: lines 34, 67, 92 catch Exception broadly. Use specific exception types.",
        "Dockerfile runs as root. Add a non-root user and use multi-stage builds to reduce image size.",
    ],
    "chat": [
        "Subject: Great connecting at the demo! I wanted to follow up on the enterprise features we discussed...",
        "Our key differentiators vs Datadog: 1) Native agent evaluation, 2) Built-in qualification framework, 3) Lower TCO.",
        "Security review talking points: SOC2 compliance, encryption at rest/transit, RBAC, audit logging.",
        "For healthcare: HIPAA compliance, PHI protection, audit trails, role-based access, data residency options.",
        "Mid-tier pricing: $49/user/month (us) vs $65/user/month (Competitor A) vs $55/user/month (Competitor B).",
        "Q3 renewal proposal: 15% volume discount for 3-year commitment, includes premium support and SLA guarantee.",
    ],
}

SESSION_ID = str(uuid.uuid4())


def _create_trace(
    experiment_name: str,
    prompt: str,
    response: str,
    agent_type: str,
    *,
    should_error: bool = False,
    latency_ms: int = 500,
    session_id: str | None = None,
):
    """Create a single trace with spans using MLflow tracing API."""
    mlflow.set_experiment(experiment_name)

    @mlflow.trace(name=f"{agent_type}-agent", span_type=SpanType.AGENT)
    def agent_call(user_input: str) -> str:
        if session_id:
            span = mlflow.get_current_active_span()
            if span:
                span.set_attribute("mlflow.trace.session", session_id)

        @mlflow.trace(name="retriever", span_type=SpanType.RETRIEVER)
        def retrieve(query: str) -> list[str]:
            time.sleep(latency_ms / 4000)
            if should_error and random.random() < 0.5:
                raise ConnectionError("Database connection timeout")
            return [f"Document chunk relevant to: {query}"]

        @mlflow.trace(name="llm-call", span_type=SpanType.LLM)
        def generate(query: str, context: list[str]) -> str:
            time.sleep(latency_ms / 2000)
            if should_error and random.random() < 0.7:
                raise RuntimeError("LLM rate limit exceeded")
            return response

        docs = retrieve(user_input)
        return generate(user_input, docs)

    try:
        result = agent_call(prompt)
        return result
    except Exception:
        return None


def seed_experiment(exp_config: dict, prompts: list[str], responses: list[str]):
    """Seed one experiment with traces, tags, and feedback."""
    name = exp_config["name"]
    agent_type = exp_config["agent_type"]
    print(f"\n=== Seeding experiment: {name} ({agent_type}) ===")

    mlflow.set_tracking_uri(TRACKING_URI)
    experiment = mlflow.set_experiment(name)
    exp_id = experiment.experiment_id
    print(f"  Experiment ID: {exp_id}")

    trace_ids = []
    for i, (prompt, response) in enumerate(zip(prompts, responses)):
        should_error = i in (2, 5)
        latency = random.randint(200, 3000)
        sess = SESSION_ID if i < 3 else None

        _create_trace(
            name, prompt, response, agent_type,
            should_error=should_error,
            latency_ms=latency,
            session_id=sess,
        )

    time.sleep(1)
    client = mlflow.MlflowClient(tracking_uri=TRACKING_URI)
    traces = client.search_traces(
        experiment_ids=[exp_id],
        max_results=50,
    )
    print(f"  Created {len(traces)} traces")

    for trace in traces:
        trace_ids.append(trace.info.trace_id)

    for i, trace in enumerate(traces):
        tid = trace.info.trace_id
        if i == 0:
            client.set_trace_tag(tid, "regression", "true")
            client.set_trace_tag(tid, "dataset", f"{name}-regression")
            client.set_trace_tag(tid, "reviewed", "true")
            print(f"  Tagged trace {tid[:12]}... as regression + reviewed")

        if i == 1:
            client.set_trace_tag(tid, "reviewed", "true")

        if i < 3:
            try:
                mlflow.log_feedback(
                    trace_id=tid,
                    name="quality",
                    value=random.choice([0.0, 0.5, 1.0]),
                    source=AssessmentSource(source_type="HUMAN", source_id="test-reviewer@example.com"),
                    rationale=f"Review of trace {i} for {name}",
                )
                print(f"  Logged feedback on trace {tid[:12]}...")
            except Exception as e:
                print(f"  Warning: feedback failed: {e}")

        if i == 0:
            try:
                mlflow.log_expectation(
                    trace_id=tid,
                    name="expected_answer",
                    value=responses[i],
                    source=AssessmentSource(source_type="HUMAN", source_id="test-reviewer@example.com"),
                )
                print(f"  Logged expectation on trace {tid[:12]}...")
            except Exception as e:
                print(f"  Warning: expectation failed: {e}")

    with mlflow.start_run(experiment_id=exp_id, run_name=f"eval-{name}-v1"):
        mlflow.log_param("profile", agent_type)
        mlflow.log_param("num_traces", len(trace_ids))
        mlflow.log_metric("pass_rate", 0.85)
        mlflow.log_metric("avg_latency_ms", 750)
        mlflow.log_metric("error_rate", 0.05)

    with mlflow.start_run(experiment_id=exp_id, run_name=f"eval-{name}-v2"):
        mlflow.log_param("profile", agent_type)
        mlflow.log_param("num_traces", len(trace_ids))
        mlflow.log_metric("pass_rate", 0.92)
        mlflow.log_metric("avg_latency_ms", 620)
        mlflow.log_metric("error_rate", 0.02)

    print(f"  Created 2 evaluation runs")
    return exp_id, trace_ids


def main():
    mlflow.set_tracking_uri(TRACKING_URI)
    print(f"MLflow tracking URI: {TRACKING_URI}")

    all_prompts = [SUPPORT_PROMPTS, CODE_REVIEW_PROMPTS, SALES_PROMPTS]
    all_responses = [RESPONSES["rag"], RESPONSES["tool-calling"], RESPONSES["chat"]]

    results = {}
    for exp_cfg, prompts, responses in zip(EXPERIMENTS, all_prompts, all_responses):
        exp_id, trace_ids = seed_experiment(exp_cfg, prompts, responses)
        results[exp_cfg["name"]] = {"experiment_id": exp_id, "trace_ids": trace_ids}

    print("\n=== Seeding complete ===")
    print(json.dumps(
        {k: {"experiment_id": v["experiment_id"], "trace_count": len(v["trace_ids"])}
         for k, v in results.items()},
        indent=2,
    ))

    output_path = os.path.join(os.path.dirname(__file__), "..", ".mlflow-test", "seed-results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSeed results saved to {output_path}")


if __name__ == "__main__":
    main()
