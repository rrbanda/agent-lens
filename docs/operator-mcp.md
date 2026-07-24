# Operator guide: official MLflow MCP

Agent Lens Hermes talks **only** to upstream official MLflow MCP
(`mlflow mcp run`), typically exposed in-cluster as Service **`mlflow-mcp`**.

This repository does **not** deploy that MCP server.

## Expected topology

| Piece | Typical location |
|-------|------------------|
| MLflow tracking | `redhat-ods-applications`, port 8443 |
| Official MCP | `redhat-ods-applications`, Service `mlflow-mcp`, port **8080**, path `/mcp` |
| Agent Lens | namespace `agent-lens`, Route `agent-lens` |

Default Hermes URL ([`agent-lens/config.yaml`](../agent-lens/config.yaml)):

```text
http://mlflow-mcp.redhat-ods-applications.svc.cluster.local:8080/mcp
```

The same URL is set as env `MLFLOW_MCP_URL` on the Agent Lens Deployment. At
startup the entrypoint copies ConfigMap `config.yaml` into Hermes home — **edit
the ConfigMap (or kustomize overlay) to change the MCP endpoint**, then roll the
Deployment. Keep `MLFLOW_MCP_URL` in sync when you change it.

## Preflight checklist

```bash
# 1. MCP pod ready
oc get pods -l app=mlflow-mcp -n redhat-ods-applications

# 2. Service exists
oc get svc mlflow-mcp -n redhat-ods-applications

# 3. Agent Lens status helper
make status

# 4. Optional: allowlist vs live tools/list
MCP_URL=http://mlflow-mcp.redhat-ods-applications.svc.cluster.local:8080/mcp \
  ./scripts/check_mcp_contract.sh
```

## Recommended MCP env (platform-owned)

| Variable | Guidance |
|----------|----------|
| `MLFLOW_TRACKING_URI` | In-cluster MLflow HTTPS URL |
| `MLFLOW_TRACKING_TOKEN` | Usually projected SA token |
| `MLFLOW_MCP_TOOLS` | Prefer GenAI tools; `all` is fine for pilots |
| `MLFLOW_WORKSPACE` | Match your MLflow workspace (often `default`) |
| TLS bundles | `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` for cluster CA |

Exact manifests are owned by the RHOAI / MLflow operator stack — not this repo.

## Network

Hermes must reach `mlflow-mcp:8080` from namespace `agent-lens`. If MCP has a
NetworkPolicy, allow ingress from the Agent Lens pod/ServiceAccount.

## Common failures

| Symptom | Check |
|---------|-------|
| Connection refused / timeout | MCP pod, Service, NetworkPolicy, wrong URL in ConfigMap |
| Tools missing in Hermes | `tools.include` in `config.yaml` vs upstream names (`./scripts/check_mcp_contract.sh`) |
| Annotate/eval fails | Judge/LLM config on MLflow side; MCP logs |
| Dashboard INACTIVE for all agents | No traces yet — see [first-trace.md](first-trace.md) |

## Related

- [limitations.md](limitations.md) — product capability contract
- [architecture.md](architecture.md) — system diagram
- [first-trace.md](first-trace.md) — seed traces before demos
