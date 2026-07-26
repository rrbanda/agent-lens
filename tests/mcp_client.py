"""Reusable MCP client for integration tests.

Communicates with MLflow MCP server via stdio transport (subprocess).
Provides synchronous tool-calling interface for test assertions.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from typing import Any


class MCPClient:
    """Wraps `mlflow mcp run` stdio server for tool calls."""

    def __init__(self, tracking_uri: str | None = None):
        self.tracking_uri = tracking_uri or os.environ.get(
            "MLFLOW_TRACKING_URI", "http://127.0.0.1:5555"
        )
        self._proc: subprocess.Popen | None = None
        self._id_counter = 0
        self._responses: dict[int, dict] = {}
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._tools: list[dict] | None = None

    def start(self) -> "MCPClient":
        env = {**os.environ, "MLFLOW_TRACKING_URI": self.tracking_uri}
        self._proc = subprocess.Popen(
            ["mlflow", "mcp", "run"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

        resp = self._send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agent-lens-test", "version": "0.1"},
            },
        )
        if "error" in resp:
            raise RuntimeError(f"MCP initialize failed: {resp['error']}")
        self._send_notification("notifications/initialized", {})
        return self

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.stdin.close()
            self._proc.wait(timeout=5)
        self._proc = None

    def _read_stdout(self):
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                msg_id = msg.get("id")
                if msg_id is not None:
                    with self._lock:
                        self._responses[msg_id] = msg
            except json.JSONDecodeError:
                pass

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def _send(self, method: str, params: dict) -> dict:
        msg_id = self._next_id()
        msg = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

        deadline = time.time() + 60
        while time.time() < deadline:
            with self._lock:
                if msg_id in self._responses:
                    return self._responses.pop(msg_id)
            time.sleep(0.05)
        raise TimeoutError(f"No response for {method} (id={msg_id}) within 60s")

    def _send_notification(self, method: str, params: dict):
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    def list_tools(self) -> list[dict]:
        resp = self._send("tools/list", {})
        tools = resp.get("result", {}).get("tools", [])
        self._tools = tools
        return tools

    def tool_names(self) -> set[str]:
        if self._tools is None:
            self.list_tools()
        return {t["name"] for t in (self._tools or [])}

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict:
        """Call an MCP tool and return the result dict (or raise on error)."""
        resp = self._send("tools/call", {"name": name, "arguments": arguments or {}})
        if "error" in resp:
            raise MCPToolError(name, resp["error"])
        return resp.get("result", {})

    def call_tool_text(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Call an MCP tool and return concatenated text content."""
        result = self.call_tool(name, arguments)
        contents = result.get("content", [])
        return "\n".join(c.get("text", "") for c in contents if c.get("type") == "text")

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


class MCPToolError(Exception):
    def __init__(self, tool_name: str, error: dict):
        self.tool_name = tool_name
        self.error = error
        super().__init__(f"Tool {tool_name} failed: {error}")
