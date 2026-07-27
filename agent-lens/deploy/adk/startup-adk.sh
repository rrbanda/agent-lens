#!/usr/bin/env bash
# OpenShell sandbox entrypoint for Agent Lens (Google ADK harness).
#
# Follows the agentic-starter-kits BYOC pattern:
# - Custom FastAPI server (adk.main:app) — NOT adk api_server
# - LiteLlm model connector — any OpenAI-compatible endpoint
# - MLflow tracing auto-enabled when MLFLOW_TRACKING_URI is set
set -euo pipefail

export PYTHONPATH="/sandbox:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

# -------------------------------------------------------------------
# 1. Copy skills from ConfigMap volume mounts into /sandbox/skills/
# -------------------------------------------------------------------
SKILLS="evaluate-agent review-trace create-regression trace-explorer quality-dashboard analyze-session audit-trail agent-registry aggregate-traces compare-evaluations executive-summary compliance-export create-judge red-team eval-loop cost-quality"

mkdir -p /sandbox/skills

for s in $SKILLS; do
  mkdir -p "/sandbox/skills/$s"
  if [ -f "/mnt/skill-$s/SKILL.md" ]; then
    cp "/mnt/skill-$s/SKILL.md" "/sandbox/skills/$s/SKILL.md"
  else
    echo "WARNING: /mnt/skill-$s/SKILL.md not found, skipping"
  fi
done

echo "Skills loaded: $(ls /sandbox/skills/ | tr '\n' ' ')"

# -------------------------------------------------------------------
# 2. Configure inference endpoint
# -------------------------------------------------------------------
echo "Model:    ${MODEL_ID:-${ADK_MODEL:-not set}}"
echo "Base URL: ${BASE_URL:-${OPENAI_BASE_URL:-not set}}"
echo "MCP:      ${MLFLOW_MCP_URL:-not set}"
echo "Tracing:  ${MLFLOW_TRACKING_URI:-disabled}"

# -------------------------------------------------------------------
# 3. Start FastAPI server (production mode)
# -------------------------------------------------------------------
PORT="${PORT:-8000}"
echo "=== Starting Agent Lens ADK on port ${PORT} ==="
exec uvicorn adk.main:app --host 0.0.0.0 --port "${PORT}"
