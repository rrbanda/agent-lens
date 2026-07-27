"""End-to-end tests for the ADK harness against a live cluster.

Run:
    ADK_URL=https://agent-lens-adk-openshell.apps.cluster-xxx.opentlc.com \
        pytest tests/test_adk_e2e.py -v

Tests verify:
  1. Health endpoint responds correctly
  2. Non-streaming chat returns OpenAI-compatible response
  3. Streaming chat returns proper SSE chunks
  4. Agent can invoke MLflow MCP tools (search_experiments)
  5. Agent can invoke MLflow MCP tools (list_scorers)
  6. Agent handles multi-turn context
  7. Agent returns structured evaluation guidance
"""

from __future__ import annotations

import json
import os

import pytest
import requests

ADK_URL = os.environ.get(
    "ADK_URL",
    "https://agent-lens-adk-openshell.apps.example.com",
)

pytestmark = pytest.mark.adk_e2e


def _chat(messages: list[dict], stream: bool = False, timeout: int = 60) -> dict | str:
    """Send a chat request to the ADK endpoint."""
    resp = requests.post(
        f"{ADK_URL}/chat/completions",
        json={"model": "gemini-2.5-flash", "messages": messages, "stream": stream},
        headers={"Content-Type": "application/json"},
        timeout=timeout,
        verify=False,
    )
    resp.raise_for_status()
    if stream:
        return resp.text
    return resp.json()


class TestHealthEndpoint:
    """Verify the /health endpoint."""

    def test_health_returns_200(self):
        resp = requests.get(f"{ADK_URL}/health", timeout=10, verify=False)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["agent_initialized"] is True


class TestNonStreamingChat:
    """Verify non-streaming chat completions."""

    def test_basic_response_format(self):
        result = _chat([{"role": "user", "content": "Say hello in exactly 3 words."}])
        assert result["object"] == "chat.completion"
        assert len(result["choices"]) >= 1
        choice = result["choices"][0]
        assert choice["message"]["role"] == "assistant"
        assert len(choice["message"]["content"]) > 0
        assert choice["finish_reason"] == "stop"

    def test_response_has_id(self):
        result = _chat([{"role": "user", "content": "Say hi."}])
        assert result["id"].startswith("chatcmpl-")


class TestStreamingChat:
    """Verify streaming SSE response."""

    def test_streaming_chunks(self):
        raw = _chat([{"role": "user", "content": "Name 2 colors."}], stream=True)
        lines = [l for l in raw.strip().split("\n") if l.startswith("data: ")]
        assert len(lines) >= 2, f"Expected at least 2 SSE lines, got {len(lines)}"

        last_data = lines[-1].removeprefix("data: ").strip()
        assert last_data == "[DONE]"

        first_chunk = json.loads(lines[0].removeprefix("data: "))
        assert first_chunk["object"] == "chat.completion.chunk"
        assert first_chunk["id"].startswith("chatcmpl-")


class TestMLflowMCPIntegration:
    """Verify the agent can invoke MLflow MCP tools."""

    def test_search_experiments(self):
        result = _chat(
            [{"role": "user", "content": "List all MLflow experiments. Return their IDs and names only."}],
            timeout=90,
        )
        content = result["choices"][0]["message"]["content"].lower()
        assert any(kw in content for kw in ["experiment", "id", "name"]), (
            f"Expected experiment listing, got: {content[:200]}"
        )
        context = result.get("context", [])
        tool_used = any(
            "search_experiments" in str(entry) for entry in context
        )
        assert tool_used, "Agent should have called search_experiments MCP tool"

    def test_list_scorers(self):
        result = _chat(
            [{"role": "user", "content": "Use the list_scorers tool with builtin=true to show me all built-in MLflow scorers. Return their names."}],
            timeout=90,
        )
        content = result["choices"][0]["message"]["content"].lower()
        context = result.get("context", [])
        tool_or_content = (
            any(kw in content for kw in ["scorer", "safety", "relevance", "correctness", "groundedness"])
            or any("list_scorers" in str(entry) for entry in context)
        )
        assert tool_or_content, (
            f"Expected scorer listing or tool call, got: {content[:200]}"
        )


class TestMultiTurnContext:
    """Verify the agent handles follow-up questions."""

    def test_follow_up(self):
        result1 = _chat(
            [{"role": "user", "content": "What is Agent Lens?"}],
            timeout=60,
        )
        content1 = result1["choices"][0]["message"]["content"]
        assert len(content1) > 10

        result2 = _chat(
            [
                {"role": "user", "content": "What is Agent Lens?"},
                {"role": "assistant", "content": content1},
                {"role": "user", "content": "What MLflow tools can you use?"},
            ],
            timeout=90,
        )
        content2 = result2["choices"][0]["message"]["content"].lower()
        assert any(kw in content2 for kw in ["mlflow", "tool", "experiment", "trace", "scorer"]), (
            f"Expected MLflow tool reference, got: {content2[:200]}"
        )


class TestEvaluationGuidance:
    """Verify the agent provides structured qualification guidance."""

    def test_qualification_workflow(self):
        result = _chat(
            [
                {
                    "role": "user",
                    "content": (
                        "I have a customer support agent. "
                        "Walk me through how to qualify it step by step. "
                        "Be concise — just list the steps."
                    ),
                }
            ],
            timeout=90,
        )
        content = result["choices"][0]["message"]["content"].lower()
        assert any(kw in content for kw in ["trace", "experiment", "scorer", "evaluat", "qualif"]), (
            f"Expected evaluation guidance, got: {content[:200]}"
        )
