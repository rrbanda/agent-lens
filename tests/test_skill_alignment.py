"""Test that analyst skills reference official upstream MLflow MCP tools only.

Agent Lens uses upstream `mlflow mcp run` (service mlflow-mcp) exclusively.
Skills must use mcp_mlflow_<tool> names that match the allowlist in
agent-lens/config.yaml. There is no in-repo FastMCP server.
"""

import os
import re

import pytest
import yaml


SKILLS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "agent-lens", "skills"
)
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "agent-lens", "config.yaml"
)
SOUL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "agent-lens", "soul.md"
)

MCP_OFFICIAL_PATTERN = re.compile(r"mcp_mlflow_(\w+)")
MCP_AGENT_LENS_PATTERN = re.compile(r"mcp_agent-lens_(\w+)")
IMPORT_MLFLOW_PATTERN = re.compile(r"import\s+mlflow|mlflow\.set_tracking_uri")


def _official_tools_from_config():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    include = cfg["mcp_servers"]["mlflow"]["tools"]["include"]
    return set(include)


def _get_skill_files():
    skills = []
    if not os.path.isdir(SKILLS_DIR):
        return skills
    for root, _dirs, files in os.walk(SKILLS_DIR):
        for f in files:
            if f == "SKILL.md":
                skills.append(os.path.join(root, f))
    return skills


def _extract_official_refs(path):
    with open(path) as f:
        content = f.read()
    return set(MCP_OFFICIAL_PATTERN.findall(content)), content


class TestSkillToolAlignment:
    """Verify skills/soul use official MLflow MCP tool names."""

    @pytest.fixture(scope="class")
    def official_tools(self):
        return _official_tools_from_config()

    @pytest.fixture(scope="class")
    def skill_files(self):
        return _get_skill_files()

    def test_skills_exist(self, skill_files):
        assert len(skill_files) > 0, "No SKILL.md files found"

    def test_config_points_at_official_mcp(self):
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        url = cfg["mcp_servers"]["mlflow"]["url"]
        assert "mlflow-mcp." in url
        assert "mlflow-mcp-server" not in url

    def test_config_has_official_tool_allowlist(self, official_tools):
        required = {
            "search_experiments",
            "search_traces",
            "get_trace",
            "evaluate_traces",
            "list_scorers",
            "log_trace_feedback",
            "log_trace_expectation",
        }
        missing = required - official_tools
        assert not missing, f"config.yaml missing official tools: {missing}"

    def test_all_tool_references_are_official(self, skill_files, official_tools):
        errors = []
        for skill_path in skill_files:
            skill_name = os.path.basename(os.path.dirname(skill_path))
            refs, _ = _extract_official_refs(skill_path)
            for tool in refs:
                if tool not in official_tools:
                    errors.append(
                        f"{skill_name}: references mcp_mlflow_{tool} "
                        f"but it is not in config.yaml tools.include"
                    )
        assert not errors, "Skill/tool misalignment:\n" + "\n".join(errors)

    def test_no_agent_lens_fastmcp_prefix(self, skill_files):
        errors = []
        paths = list(skill_files) + [SOUL_PATH]
        for path in paths:
            label = os.path.basename(path) if path.endswith("soul.md") else (
                os.path.basename(os.path.dirname(path))
            )
            with open(path) as f:
                content = f.read()
            bad = MCP_AGENT_LENS_PATTERN.findall(content)
            if bad:
                errors.append(f"{label}: uses mcp_agent-lens_* (FastMCP): {bad}")
        assert not errors, "Must use official mcp_mlflow_* only:\n" + "\n".join(errors)

    def test_no_sandbox_import_mlflow(self, skill_files):
        errors = []
        paths = list(skill_files) + [SOUL_PATH]
        for path in paths:
            label = os.path.basename(path) if path.endswith("soul.md") else (
                os.path.basename(os.path.dirname(path))
            )
            with open(path) as f:
                content = f.read()
            # Allow mentioning the anti-pattern in prose; block executable snippets.
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith(">"):
                    continue
                if "Never" in stripped or "Do not" in stripped or "do not" in stripped:
                    continue
                if IMPORT_MLFLOW_PATTERN.search(stripped) and stripped.startswith(
                    ("import ", "from ", "mlflow.")
                ):
                    errors.append(f"{label}:{i}: {stripped}")
        assert not errors, "Sandbox must not teach import mlflow:\n" + "\n".join(errors)

    def test_soul_references_official_prefix(self):
        with open(SOUL_PATH) as f:
            soul = f.read()
        assert "mcp_mlflow_" in soul
        assert "upstream official MLflow MCP" in soul
