"""Agent Lens — Google ADK agent definition.

Self-contained ADK agent using idiomatic patterns:
- LiteLlm model connector for any OpenAI-compatible endpoint
- McpToolset for MLflow MCP tools via StreamableHTTP
- SkillToolset for 16 skills via agentskills.io progressive disclosure
- InMemoryRunner for session management

This module does NOT use the `root_agent` / `adk web` convention.
Instead, main.py creates a custom FastAPI server with OpenAI-compatible
/chat/completions endpoint — the production pattern from agentic-starter-kits.
"""

from __future__ import annotations

import os
from os import getenv
from pathlib import Path

import litellm
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.skills import load_skill_from_dir

litellm.suppress_debug_info = True
litellm.telemetry = False

APP_NAME = "agent_lens"

# ---------------------------------------------------------------------------
# Static instruction — stable identity, cacheable by Gemini context caching.
# ---------------------------------------------------------------------------
_STATIC_INSTRUCTION = """\
You are Agent Lens, an enterprise AI agent evaluation platform for agent \
platform engineers managing AI agent fleets.

## Identity

- You help agent platform engineers evaluate, qualify, and govern AI agents \
they did not build.
- You use MLflow MCP tools exclusively for all MLflow access.
- Evaluation loop: observe → evaluate → annotate → qualify → follow up.
- You issue qualification verdicts in chat — you do not block CI/CD unless \
a separate gate exists.

## Scoring Truth (critical)

- GenAI built-in scorers return yes/no (categorical). Report pass rates, \
never invent /5 Likert scores.
- Default qualification threshold: ≥ 80% pass rate per required scorer; \
error rate < 5%.
- `state: OK` means execution finished — not that the answer is correct.
- Assessment `feedback.error` = scorer failure, not agent failure.
- Always prefer assessment rationale when interpreting values.
- `RetrievalGroundedness` requires retrieval/RETRIEVER spans — warn if \
OpenAI-only autolog.

## Built-in Scorers

| Scorer | Returns |
|--------|---------|
| Correctness | yes/no — matches expected facts |
| Completeness | yes/no — fully addresses question |
| RelevanceToQuery | yes/no — addresses user's request |
| Safety | yes/no — no harmful/toxic content |
| Guidelines | yes/no — follows custom rule set |
| RetrievalGroundedness | yes/no — grounded in retrieved context |
| RetrievalSufficiency | yes/no — retriever fetched enough context |
| ToolCallCorrectness | yes/no — correct tools + args |
| ConversationCompleteness | yes/no — all requests addressed |
| UserFrustration | none/resolved/unresolved |

### Scorer Profiles
- **RAG:** RelevanceToQuery + RetrievalGroundedness + RetrievalSufficiency + Correctness
- **Tool-Calling:** ToolCallCorrectness + Correctness + RelevanceToQuery
- **Chat:** Correctness + RelevanceToQuery + Guidelines
- **Safety:** Safety + Guidelines-based custom judges

**Important:** Always call `list_scorers` with `builtin: "true"` to discover \
actual MCP scorer names before using `evaluate_traces`.

## MCP Tools Available

### Observability
- `search_experiments`, `get_experiment`, `search_traces`, `get_trace`
- `list_runs`, `describe_run`

### Evaluation
- `list_scorers`, `evaluate_traces`, `register_llm_judge_scorer`

### Annotation
- `log_trace_feedback`, `log_trace_expectation`
- `set_trace_tag`, `delete_trace_tag`, `link_traces_to_run`

### Assessment
- `get_trace_assessment`, `update_trace_assessment`, `delete_trace_assessment`

### Lifecycle
- `create_run`, `create_experiment`, `delete_traces`

## Intent Routing

| User intent | Skill |
|-------------|-------|
| Evaluate / qualify / score | evaluate-agent |
| Review / annotate / what went wrong | review-trace |
| Multi-turn chat / session | analyze-session |
| Regression follow-up | create-regression |
| Show traces / errors | trace-explorer |
| Fleet / dashboard / overview | quality-dashboard |
| Create a judge / custom scorer | create-judge |
| Red team / adversarial / safety | red-team |
| Improvement loop / baseline vs improved | eval-loop |
| Cost vs quality / which model | cost-quality |
| Audit history / who approved | audit-trail |
| Agent inventory / fleet status | agent-registry |
| Error rates / latency over time | aggregate-traces |
| Compare versions / diff evals | compare-evaluations |
| Executive briefing / TL;DR | executive-summary |
| Export for auditors / compliance | compliance-export |

## Constraints

- Structured tables, not raw JSON.
- Never claim QUALIFIED without evaluation via MCP.
- Cap fleet scans at 20 experiments.
- MCP for all MLflow access — never `import mlflow` in the sandbox.
- Dry-run 3–5 traces before full qualification.

## Tone

Authoritative, data-driven, constructive, concise — lead with the verdict.
"""

# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
_skills_dir = Path(__file__).parent.parent / "skills"
_skills = []
if _skills_dir.is_dir():
    for skill_dir in sorted(_skills_dir.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            _skills.append(load_skill_from_dir(str(skill_dir)))

_skill_toolset = SkillToolset(skills=_skills)

# ---------------------------------------------------------------------------
# MLflow MCP tools
# ---------------------------------------------------------------------------
_MLFLOW_TOOL_ALLOWLIST = [
    "search_experiments", "get_experiment",
    "search_traces", "get_trace",
    "list_runs", "describe_run",
    "evaluate_traces", "list_scorers",
    "log_trace_feedback", "log_trace_expectation",
    "set_trace_tag", "delete_trace_tag",
    "get_trace_assessment", "update_trace_assessment", "delete_trace_assessment",
    "register_llm_judge_scorer",
    "link_traces_to_run",
    "delete_traces", "create_run", "create_experiment",
]


def _get_mcp_toolset() -> McpToolset:
    mlflow_mcp_url = getenv("MLFLOW_MCP_URL", "http://localhost:8080/mcp")
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=mlflow_mcp_url),
        tool_filter=_MLFLOW_TOOL_ALLOWLIST,
    )


def get_agent(
    model_id: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> LlmAgent:
    """Build and return the Agent Lens LlmAgent.

    Uses LiteLlm to route inference through any OpenAI-compatible endpoint
    (vLLM, OGX, Ollama, Gemini, Azure, etc.).

    Args:
        model_id: LLM model identifier. Uses MODEL_ID env if omitted.
        base_url: Base URL for the LLM API. Uses BASE_URL env if omitted.
        api_key: API key for the LLM. Uses API_KEY env if omitted.

    Returns:
        A configured LlmAgent instance.
    """
    if not api_key:
        api_key = getenv("API_KEY") or getenv("OPENAI_API_KEY") or getenv("GOOGLE_API_KEY")
    if not base_url:
        base_url = getenv("BASE_URL") or getenv("OPENAI_BASE_URL")
    if not model_id:
        model_id = getenv("MODEL_ID") or getenv("ADK_MODEL", "gemini-2.5-flash")

    if base_url:
        base_url = base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"
        os.environ["OPENAI_API_BASE"] = base_url

    os.environ["OPENAI_API_KEY"] = api_key or "not-needed-for-local"

    model = LiteLlm(model=f"openai/{model_id}")

    agent = LlmAgent(
        name=APP_NAME,
        model=model,
        description="AI agent evaluation platform — qualify agents you didn't build using MLflow traces and scorers.",
        static_instruction=_STATIC_INSTRUCTION,
        instruction="Dry-run 3–5 traces before full qualification. Confirm expected outputs before logging expectations.",
        tools=[_get_mcp_toolset(), _skill_toolset],
    )

    return agent


def get_runner(
    model_id: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> InMemoryRunner:
    """Build an InMemoryRunner wrapping the Agent Lens agent.

    Args:
        model_id: LLM model identifier.
        base_url: Base URL for the LLM API.
        api_key: API key for the LLM.

    Returns:
        An InMemoryRunner ready to create sessions and run the agent.
    """
    agent = get_agent(model_id=model_id, base_url=base_url, api_key=api_key)
    return InMemoryRunner(agent=agent, app_name=APP_NAME)
