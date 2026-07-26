#!/usr/bin/env bash
# Compare agent-lens/config.yaml tools.include against a live MCP tools/list.
# Usage:
#   MCP_URL=http://host:8080/mcp ./scripts/check_mcp_contract.sh
#
# The script reads the official MCP tools from config.yaml and verifies they
# exist on the remote server. LoggedModel tools (SDK-only, proxied via Gateway)
# are excluded from validation -- see ADR-001.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${ROOT}/agent-lens/config.yaml"
MCP_URL="${MCP_URL:-http://mlflow-mcp.redhat-ods-applications.svc.cluster.local:8080/mcp}"

if ! command -v python3 >/dev/null; then
  echo "python3 required" >&2
  exit 2
fi

python3 - "$CONFIG" "$MCP_URL" <<'PY'
import json, sys, urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

config_path, mcp_url = sys.argv[1], sys.argv[2]
cfg = yaml.safe_load(Path(config_path).read_text())
want = set(cfg["mcp_servers"]["mlflow"]["tools"]["include"])

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {},
}
req = urllib.request.Request(
    mcp_url,
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode()
except Exception as e:
    print(f"FAIL: could not reach {mcp_url}: {e}", file=sys.stderr)
    print("Allowlist in config.yaml (offline):")
    for t in sorted(want):
        print(f"  - {t}")
    sys.exit(1)

text = body.strip()
if text.startswith("event:") or "data:" in text:
    chunks = []
    for line in text.splitlines():
        if line.startswith("data:"):
            chunks.append(line[5:].strip())
    text = chunks[-1] if chunks else text

try:
    msg = json.loads(text)
except json.JSONDecodeError:
    print("FAIL: non-JSON response from MCP (try from a pod with cluster DNS)", file=sys.stderr)
    print(text[:500], file=sys.stderr)
    sys.exit(1)

tools = msg.get("result", {}).get("tools") or msg.get("tools") or []
have = {t.get("name") for t in tools if isinstance(t, dict) and t.get("name")}
if not have:
    print("FAIL: tools/list returned no tool names", file=sys.stderr)
    print(json.dumps(msg, indent=2)[:1000], file=sys.stderr)
    sys.exit(1)

missing = sorted(want - have)
extra_note = sorted(have - want)
print(f"MCP URL: {mcp_url}")
print(f"Allowlisted: {len(want)}  Remote: {len(have)}")
if missing:
    print("MISSING from remote (Hermes allowlist will hide/break these):")
    for t in missing:
        print(f"  - {t}")
    sys.exit(1)
print("OK: all allowlisted tools present on remote MCP")
if extra_note:
    print(f"(Remote also has {len(extra_note)} tools not in allowlist — fine)")
sys.exit(0)
PY
