"""Test that all skills reference valid MCP tool names.

Parses SKILL.md files and verifies that every referenced tool name
(mcp_agent-lens_*) exists in the MCP server's entrypoint.py.
"""

import os
import re

import pytest


SKILLS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "analyst-agent", "skills"
)
ENTRYPOINT = os.path.join(
    os.path.dirname(__file__), "..", "mcp-server", "entrypoint.py"
)

MCP_TOOL_PATTERN = re.compile(r"mcp_agent-lens_(\w+)")
FUNC_DEF_PATTERN = re.compile(r"^def (\w+)\(", re.MULTILINE)


def _get_registered_tools():
    """Extract all function names decorated with @mcp.tool() from entrypoint."""
    with open(ENTRYPOINT) as f:
        source = f.read()

    tools = set()
    lines = source.split("\n")
    for i, line in enumerate(lines):
        if "@mcp.tool()" in line:
            for j in range(i + 1, min(i + 5, len(lines))):
                match = FUNC_DEF_PATTERN.match(lines[j])
                if match:
                    tools.add(match.group(1))
                    break
    return tools


def _get_skill_files():
    """Find all SKILL.md files in the skills directory."""
    skills = []
    if not os.path.isdir(SKILLS_DIR):
        return skills
    for root, dirs, files in os.walk(SKILLS_DIR):
        for f in files:
            if f == "SKILL.md":
                skills.append(os.path.join(root, f))
    return skills


def _extract_tool_references(skill_path):
    """Extract all mcp_agent-lens_* tool references from a skill file."""
    with open(skill_path) as f:
        content = f.read()
    return set(MCP_TOOL_PATTERN.findall(content))


class TestSkillToolAlignment:
    """Verify all skills reference existing MCP tools."""

    @pytest.fixture(scope="class")
    def registered_tools(self):
        return _get_registered_tools()

    @pytest.fixture(scope="class")
    def skill_files(self):
        return _get_skill_files()

    def test_skills_exist(self, skill_files):
        """At least one skill file should exist."""
        assert len(skill_files) > 0, "No SKILL.md files found"

    def test_entrypoint_has_tools(self, registered_tools):
        """Entrypoint should have registered tools."""
        assert len(registered_tools) > 0, "No @mcp.tool() functions found"

    def test_all_tool_references_are_valid(self, skill_files, registered_tools):
        """Every mcp_agent-lens_* reference in skills must map to a real tool."""
        errors = []
        for skill_path in skill_files:
            skill_name = os.path.basename(os.path.dirname(skill_path))
            referenced_tools = _extract_tool_references(skill_path)
            for tool in referenced_tools:
                if tool not in registered_tools:
                    errors.append(f"{skill_name}: references mcp_agent-lens_{tool} but no '{tool}' function exists")

        assert not errors, "Skill/tool misalignment:\n" + "\n".join(errors)

    def test_no_legacy_tool_references(self, skill_files):
        """No skills should reference the old mcp_mlflow_* prefix."""
        legacy_pattern = re.compile(r"mcp_mlflow_(\w+)")
        errors = []
        for skill_path in skill_files:
            skill_name = os.path.basename(os.path.dirname(skill_path))
            with open(skill_path) as f:
                content = f.read()
            legacy_refs = legacy_pattern.findall(content)
            if legacy_refs:
                errors.append(f"{skill_name}: still uses legacy mcp_mlflow_* references: {legacy_refs}")

        assert not errors, "Legacy tool references found:\n" + "\n".join(errors)

    def test_core_tools_registered(self, registered_tools):
        """Critical tools for the AgentOps loop must exist."""
        required_tools = [
            "list_experiments",
            "search_traces",
            "run_evaluation",
            "annotate_trace",
            "check_quality_gate",
            "create_test_case",
            "get_review_queue",
            "health_check",
        ]
        missing = [t for t in required_tools if t not in registered_tools]
        assert not missing, f"Missing critical tools: {missing}"
