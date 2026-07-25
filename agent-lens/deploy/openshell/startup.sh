#!/usr/bin/env bash
# OpenShell sandbox entrypoint for Agent Lens.
# Hermes v0.19+ has built-in dashboard auth — no stubs needed.
set -euo pipefail

export HOME=/sandbox
export HERMES_HOME=/sandbox/.hermes
export PATH="/sandbox/.venv/bin:/usr/local/bin:${PATH}"

if ! command -v hermes >/dev/null 2>&1; then
  echo "ERROR: hermes not found. Rebuild image with agent-lens/Containerfile." >&2
  exit 1
fi

echo "Hermes $(hermes --version 2>&1 || true)"

SKILLS="evaluate-agent review-trace create-regression trace-explorer quality-dashboard analyze-session"

mkdir -p \
  /sandbox/.hermes/skills \
  /sandbox/.hermes/memory \
  /sandbox/.hermes/sessions \
  /sandbox/.hermes/profiles \
  /sandbox/.hermes/auto-skills \
  /sandbox/.hermes/db \
  /sandbox/data \
  /sandbox/output

for s in $SKILLS; do
  mkdir -p "/sandbox/.hermes/skills/$s"
  cp "/mnt/skill-$s/SKILL.md" "/sandbox/.hermes/skills/$s/SKILL.md"
done

cp /mnt/soul/SOUL.md /sandbox/.hermes/SOUL.md
cp /mnt/config/config.yaml /sandbox/.hermes/config.yaml

python3 <<PY
import os, yaml
with open("/sandbox/.hermes/config.yaml") as f:
    cfg = yaml.safe_load(f)

cfg.setdefault("skills", {})["directory"] = "/sandbox/.hermes/skills"

cfg.setdefault("model", {})
cfg["model"]["default"] = os.environ.get("LLAMASTACK_MODEL", "gemini/models/gemini-2.5-flash")
cfg["model"]["base_url"] = os.environ.get("OPENAI_BASE_URL", "http://llamastack-service.llamastack.svc:8321/v1")
cfg["model"]["provider"] = "custom"
cfg["model"]["api_key"] = os.environ.get("OPENAI_API_KEY", "not-needed")

mcp_url = os.environ.get("MLFLOW_MCP_URL")
if mcp_url:
    cfg.setdefault("mcp_servers", {}).setdefault("mlflow", {})["url"] = mcp_url

with open("/sandbox/.hermes/config.yaml", "w") as f:
    yaml.dump(cfg, f, default_flow_style=False)
print("Config updated: model, MCP URL")
print("Skills:", ", ".join(sorted(os.listdir("/sandbox/.hermes/skills"))))
PY

echo "=== Starting Hermes gateway (background) ==="
hermes gateway run > /tmp/hermes-gateway.log 2>&1 &
sleep 5

echo "=== Starting Hermes dashboard ==="
exec hermes dashboard \
  --host "${HERMES_DASHBOARD_HOST:-0.0.0.0}" \
  --port "${HERMES_DASHBOARD_PORT:-9119}" \
  --no-open --skip-build --insecure
