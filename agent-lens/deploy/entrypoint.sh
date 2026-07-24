#!/usr/bin/env bash
# Runtime-only entrypoint. Dependencies MUST be baked into the image (Containerfile).
# Never pip-install or download Node at pod start.
set -euo pipefail

if ! command -v hermes >/dev/null 2>&1; then
  echo "ERROR: hermes not found in image PATH. Rebuild with agent-lens/Containerfile." >&2
  exit 1
fi

SKILLS="evaluate-agent review-trace create-regression trace-explorer quality-dashboard analyze-session"

mkdir -p /persistent/memory /persistent/sessions /persistent/profiles /persistent/auto-skills /persistent/db
mkdir -p /tmp/work/.local /tmp/work/data /tmp/work/output /tmp/work/.hermes

ln -sfn /persistent/memory /tmp/work/.hermes/memory
ln -sfn /persistent/sessions /tmp/work/.hermes/sessions
ln -sfn /persistent/profiles /tmp/work/.hermes/profiles
ln -sfn /persistent/auto-skills /tmp/work/.hermes/auto-skills
ln -sfn /persistent/db /tmp/work/.hermes/db

for f in USER.md MEMORY.md; do
  [ -f "/persistent/$f" ] && cp "/persistent/$f" "/tmp/work/.hermes/$f"
done

for s in $SKILLS; do
  mkdir -p "/tmp/work/.hermes/skills/$s"
done

cp /mnt/skill-evaluate-agent/SKILL.md /tmp/work/.hermes/skills/evaluate-agent/SKILL.md
cp /mnt/skill-review-trace/SKILL.md /tmp/work/.hermes/skills/review-trace/SKILL.md
cp /mnt/skill-create-regression/SKILL.md /tmp/work/.hermes/skills/create-regression/SKILL.md
cp /mnt/skill-trace-explorer/SKILL.md /tmp/work/.hermes/skills/trace-explorer/SKILL.md
cp /mnt/skill-quality-dashboard/SKILL.md /tmp/work/.hermes/skills/quality-dashboard/SKILL.md
cp /mnt/skill-analyze-session/SKILL.md /tmp/work/.hermes/skills/analyze-session/SKILL.md

cp /mnt/soul/SOUL.md /tmp/work/.hermes/SOUL.md
cp /mnt/config/config.yaml /tmp/work/.hermes/config.yaml

HASH=$(python3 -c "
import hashlib, secrets, base64, os
pw = os.environ.get('DASHBOARD_PASSWORD', '')
if not pw:
    raise ValueError('DASHBOARD_PASSWORD must be set via secret')
salt = secrets.token_bytes(16)
key = hashlib.scrypt(pw.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
s = base64.b64encode(salt).decode()
k = base64.b64encode(key).decode()
print(f'scrypt\$16384\$8\$1\${s}\${k}')
")

python3 <<PY
import os, yaml
with open('/tmp/work/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
cfg['dashboard']['basic_auth']['password_hash'] = """${HASH}"""
mcp_url = os.environ.get('MLFLOW_MCP_URL')
if mcp_url:
    cfg.setdefault('mcp_servers', {}).setdefault('mlflow', {})['url'] = mcp_url
api_key = os.environ.get('API_SERVER_KEY')
if api_key:
    cfg['api_server_key'] = api_key
    cfg.setdefault('platforms', {}).setdefault('api_server', {}).setdefault('extra', {})['key'] = api_key
with open('/tmp/work/.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False)
print('Config updated: password hash, MCP URL, API key')
PY

trap 'cp /tmp/work/.hermes/USER.md /tmp/work/.hermes/MEMORY.md /persistent/ 2>/dev/null || true; echo State saved' SIGTERM SIGINT

echo "=== Starting Hermes gateway (background) ==="
hermes gateway run > /tmp/hermes-gateway.log 2>&1 &
sleep 5

echo "=== Starting Hermes dashboard ==="
exec hermes dashboard --host 0.0.0.0 --port 18789 --no-open --skip-build
