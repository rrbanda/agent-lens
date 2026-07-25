# Agent Lens -- Hermes Evaluation Agent on OpenShell

Conversational evaluation for platform teams via **upstream official MLflow MCP**.
Production runtime: **NVIDIA OpenShell Sandbox** in namespace `openshell`.

> The OpenShift install path should be treated as experimental and not used in production.
> Based on [Set Up OpenShell on Kubernetes](https://docs.nvidia.com/openshell/latest/kubernetes/)
> and [Set Up OpenShell on OpenShift](https://docs.nvidia.com/openshell/latest/openshift/).

## Architecture

Agent Lens is a three-layer stack:

| Layer | Component | Role |
|-------|-----------|------|
| Agent harness | [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.19.0+ | Dashboard UI, gateway, skill system, chat |
| Secure runtime | [NVIDIA OpenShell](https://github.com/nvidia/openshell) v0.0.85 | Supervisor wraps Hermes with Landlock + seccomp sandbox |
| Orchestration | [Agent Sandbox Controller](https://github.com/kubernetes-sigs/agent-sandbox) v0.5.x | Reconciles `Sandbox` CRs into supervised pods |

```
Platform Engineer
    |  HTTPS
    v
OpenShift Route (TLS edge)
    |
Service :9119
    |
+-- agent-lens Sandbox Pod ----------------------------+
|  OpenShell Supervisor (--mode=process)               |
|    -> Hermes Dashboard (port 9119)                   |
|         |-> MLflow MCP (port 8080, mcp_mlflow_*)     |
|         |-> LlamaStack (port 8321, OpenAI API)       |
+------------------------------------------------------+
    ^
    |  reconciles Sandbox CR
Agent Sandbox Controller (agent-sandbox-system ns)
```

## Prerequisites

- OpenShift 4.18+ cluster with `oc` CLI authenticated
- Helm 3.x
- `kustomize` CLI (or `oc apply -k` fallback)
- LlamaStack inference service in `llamastack` namespace (port 8321)
- Official MLflow MCP service in `redhat-ods-applications` namespace (port 8080)

## Platform setup (one-time)

### 1. Kubernetes Agent Sandbox

**Option 1 (Recommended)** -- Deploy the Red Hat build of Agent Sandbox v0.9.0.
Follow the installation instructions at
[Deploying Red Hat build of Agent Sandbox](https://docs.redhat.com/en/documentation/red_hat_build_of_agent_sandbox).

**Option 2** -- Deploy the upstream k8s sandbox operator:

```bash
# Check if the cluster already has the CRDs
oc get crd | grep sandbox

# Install core components
kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/latest/download/manifest.yaml

# Install extension components
kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/latest/download/extensions.yaml
```

Both options create CRDs (`Sandbox`, `SandboxClaim`, `SandboxTemplate`,
`SandboxWarmPool`) in `v1beta1`, the `agent-sandbox-system` namespace, and the
`agent-sandbox-controller` deployment.

To uninstall:

```bash
kubectl delete agentsandboxes --all --all-namespaces
kubectl delete -f https://github.com/kubernetes-sigs/agent-sandbox/releases/latest/download/manifest.yaml
```

### 2. Namespace and SCC

Pre-create the namespace so the SCC binding can be applied before the Helm chart installs:

```bash
oc create ns openshell
oc adm policy add-scc-to-user privileged -z openshell-sandbox -n openshell
```

### 3. Install OpenShell Gateway

[Helm chart reference](https://github.com/NVIDIA/OpenShell/blob/main/deploy/helm/openshell/README.md).

The `podSecurityContext.fsGroup=null` and `securityContext.runAsUser=null` overrides
are **required on OpenShift** -- without them the gateway pod fails SCC validation
(`restricted-v2` rejects the Helm defaults of `runAsUser: 1000` / `fsGroup: 1000`).

```bash
helm install openshell oci://ghcr.io/nvidia/openshell/helm-chart \
  --version 0.0.85 \
  --namespace openshell \
  --set podSecurityContext.fsGroup=null \
  --set securityContext.runAsUser=null \
  --set server.auth.allowUnauthenticatedUsers=true
```

Wait for rollout and verify:

```bash
oc -n openshell rollout status statefulset/openshell
oc get pods -n openshell   # gateway pod should be 1/1 Running
```

### 4. mTLS client authentication

The Helm chart auto-generates a mutual TLS (mTLS) certificate bundle. Extract it
so the `openshell` CLI on your local machine can connect to the gateway over
port-forward. This mTLS bundle is for **transport security** (encryption), not user
authentication. For user auth, configure
[OIDC](https://docs.nvidia.com/openshell/latest/reference/gateway-auth#oidc) or a
trusted access proxy.

```bash
mkdir -p ~/.config/openshell/gateways/openshift/mtls

oc -n openshell get secret openshell-client-tls \
  -o jsonpath='{.data.ca\.crt}'  | base64 -d \
  > ~/.config/openshell/gateways/openshift/mtls/ca.crt

oc -n openshell get secret openshell-client-tls \
  -o jsonpath='{.data.tls\.crt}' | base64 -d \
  > ~/.config/openshell/gateways/openshift/mtls/tls.crt

oc -n openshell get secret openshell-client-tls \
  -o jsonpath='{.data.tls\.key}' | base64 -d \
  > ~/.config/openshell/gateways/openshift/mtls/tls.key
```

### 5. Local CLI setup

Install the `openshell` CLI:

```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
```

Enable port forwarding and register the gateway:

```bash
oc -n openshell port-forward svc/openshell 8080:8080

openshell gateway add https://127.0.0.1:8080 --local --name openshift
```

Verify connectivity:

```bash
openshell status
openshell gateway list
```

### 6. Provider and inference settings

Register LLM provider credentials with the gateway so sandboxes can use them for
inference. Example with Google Vertex AI:

```bash
openshell provider create \
  --name vertex-prod \
  --type google-vertex-ai \
  --from-gcloud-adc \
  --config VERTEX_AI_PROJECT_ID=<your-project> \
  --config VERTEX_AI_REGION=global
```

Enable the v2 provider pipeline and set the default model:

```bash
openshell settings set --global --key providers_v2_enabled --value true --yes
openshell inference set --provider vertex-prod --model <your-model>
```

For Agent Lens, inference is configured via env vars (`OPENAI_BASE_URL` pointing to
LlamaStack) rather than the gateway provider pipeline.

### 7. Create dashboard secret

```bash
make secret-openshell   # prompts for dashboard password + API key
```

This creates secret `agent-lens-auth` in the `openshell` namespace with keys
`dashboard-password` and `api-server-key`.

### Uninstall OpenShell

```bash
helm uninstall openshell -n openshell

oc -n openshell delete secret openshell-jwt-keys \
  openshell-server-tls openshell-client-tls
```

## Agent harness

Agent Lens uses an **agent harness** to run the evaluation agent inside the sandbox.
The harness is the framework that provides the dashboard UI, chat interface, skill
system, and MCP client. The harness is **pluggable** -- a different framework can be
substituted by changing the Containerfile and startup.sh.

### Current harness: Hermes Agent

[Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.19.0+ is the current
harness. It provides:

- Web dashboard with cookie-based auth (`/auth/password-login`)
- Built-in MCP client (SSE / streamable-http transport)
- Skill system (directory-based SKILL.md files)
- Gateway for API access
- Session persistence (SQLite in PVC)

### Swapping to a different harness

To use a different harness (e.g. LangGraph, CrewAI, a custom framework):

1. **Containerfile** -- replace `hermes-agent` with your framework's dependencies
2. **startup.sh** -- replace the `hermes gateway run` + `hermes dashboard` commands
   with your framework's server startup; ensure it listens on port 9119
3. **config.yaml** -- replace with your framework's configuration format; keep the
   same MCP server URL, model, and tool allowlist
4. **soul.md / skills/** -- adapt to your framework's prompt or agent definition format
5. **sandbox.yaml** -- no changes needed; the supervisor, volumes, and env vars are
   harness-agnostic

The OpenShell sandbox, mTLS, network policies, Landlock/seccomp, and the Sandbox CR
are all harness-independent. Only the container image and entrypoint change.

## Agent configuration (Hermes)

### config.yaml

[config.yaml](config.yaml) defines the Hermes agent behavior:

```yaml
model:
  default: "gemini/models/gemini-2.5-flash"
  base_url: "http://llamastack-service.llamastack.svc:8321/v1"
  provider: custom
  api_key: "not-needed"

mcp_servers:
  mlflow:
    url: "http://mlflow-mcp.redhat-ods-applications.svc.cluster.local:8080/mcp"
    timeout: 180
    connect_timeout: 60
    tools:
      include:
        - search_experiments
        - get_experiment
        - search_traces
        - get_trace
        - log_trace_feedback
        - log_trace_expectation
        - set_trace_tag
        - evaluate_traces
        - list_runs
        - describe_run
        - list_scorers
```

| Section | Key settings |
|---------|-------------|
| `model` | LLM model name, base URL (LlamaStack), provider type, API key |
| `mcp_servers.mlflow` | URL, timeouts, tool allowlist (11 tools from official MLflow MCP) |
| `tools` | `code_execution: on` (local), `file_operations: on`, web/browser off |
| `toolsets` | skills, memory, session_search, delegation enabled |
| `skills` | directory `/sandbox/.hermes/skills`, curator enabled |

`startup.sh` patches this file at boot with env var overrides (`OPENAI_BASE_URL`,
`LLAMASTACK_MODEL`, `MLFLOW_MCP_URL`), so env vars are the runtime source of truth.

### soul.md

[soul.md](soul.md) defines agent identity:

- Agent Lens is an enterprise evaluation platform for platform teams
- Allowed MCP tools: observability (`search_traces`, `get_trace`, ...), evaluation
  (`evaluate_traces`, `list_scorers`), annotation (`log_trace_feedback`, ...)
- Scoring truth: GenAI scorers are yes/no categorical; report **pass rates**, never
  invent Likert scores
- Scorer profiles: RAG, Tool-Calling, Chat
- Certification threshold: >= 80% pass rate, < 5% error rate
- Intent routing table maps user intents to skills

### Skills

Six skills in [skills/](skills/), each a `SKILL.md` mounted as a ConfigMap:

| Skill | Trigger | MCP tools used |
|-------|---------|---------------|
| `evaluate-agent` | Evaluate, Score, Certify | `evaluate_traces`, `list_scorers` |
| `review-trace` | Review, Annotate | `get_trace`, `search_traces`, `log_trace_feedback`, `log_trace_expectation` |
| `analyze-session` | Chat session / multi-turn | `search_traces`, `get_trace` |
| `create-regression` | Regression follow-up | `log_trace_expectation`, `set_trace_tag` |
| `trace-explorer` | Show traces, Errors | `search_traces`, `get_trace` |
| `quality-dashboard` | Overview, Fleet health | `search_experiments`, `search_traces`, `list_runs` (max 20) |

## Startup sequence

[deploy/openshell/startup.sh](deploy/openshell/startup.sh) is the pod entrypoint,
run by the OpenShell supervisor. It executes these steps in order:

1. **Verify hermes is installed** -- exits with error if not found (runtime pip is
   blocked by Landlock, so all deps must be baked into the image)
2. **Create directory structure** -- `/sandbox/.hermes/{skills,memory,sessions,profiles,auto-skills,db}`,
   `/sandbox/{data,output}`
3. **Copy skills from ConfigMaps** -- each skill's `SKILL.md` is mounted at
   `/mnt/skill-<name>/` and copied to `/sandbox/.hermes/skills/<name>/SKILL.md`
4. **Copy soul and config** -- from `/mnt/soul/SOUL.md` and `/mnt/config/config.yaml`
   to `/sandbox/.hermes/`
5. **Patch config.yaml with env vars** -- a Python script overwrites `model.default`,
   `model.base_url`, `model.api_key`, and `mcp_servers.mlflow.url` from env vars
   (`LLAMASTACK_MODEL`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `MLFLOW_MCP_URL`).
   This means env vars on the Sandbox CR are the runtime source of truth.
6. **Start Hermes gateway** -- `hermes gateway run` in the background (API access)
7. **Start Hermes dashboard** -- `exec hermes dashboard` with `--host 0.0.0.0`,
   `--port 9119`, `--no-open`, `--skip-build`, `--insecure`. The `--insecure` flag
   disables the OAuth gate so the dashboard can bind to `0.0.0.0` (non-loopback)
   with basic auth only.

### Dashboard login flow

Hermes v0.19.0 uses cookie-based authentication:

- `GET /login` -- returns the sign-in page
- `POST /auth/password-login` with JSON body `{"provider":"basic","username":"admin",
  "password":"...","next":"/"}` -- returns `{"ok":true}` and sets a session cookie
- Subsequent API calls use the session cookie (not a Bearer token)
- Username: `admin`, password: from secret `agent-lens-auth` key `dashboard-password`

## Container image

[Containerfile](Containerfile) uses `python:3.13-slim` as base:

- **Python 3.13 is required.** `hermes-agent>=0.16.0` declares `requires-python: <3.14`.
  The NVIDIA OpenShell sandbox base image ships Python 3.14, which silently downgrades
  hermes to the broken v0.15.2. Using Python 3.13 avoids this entirely.
- **Lightweight base (~150MB vs 4GB)** avoids `BuildPodEvicted` errors from ephemeral
  storage pressure during in-cluster builds.
- The OpenShell supervisor is injected via init container, not from the base image.
- All dependencies baked at build time. The supervisor's Landlock + seccomp sandbox
  **blocks pip at runtime** (no network, no filesystem writes outside allowed paths).

Installed packages: `hermes-agent>=0.19.0`, `aiohttp`, `mcp`, `pyyaml`, `fastapi`,
`uvicorn[standard]`, `websockets`, Node.js 22.x.

## Sandbox pod structure

Defined in [deploy/openshell/sandbox.yaml](deploy/openshell/sandbox.yaml):

### Init containers

1. **`openshell-supervisor-install`** -- copies supervisor binary from
   `ghcr.io/nvidia/openshell/supervisor:0.0.85` to shared emptyDir `/opt/openshell/bin/`
2. **`workspace-init`** -- copies `/sandbox` to PVC on first run (persists Hermes state
   across restarts; skips if `.workspace-initialized` exists)

### Main container

Runs the supervisor which wraps `startup.sh`. The `openshell-client-tls` secret is
mounted at `/etc/openshell-tls/` so the supervisor can authenticate to the gateway
over mTLS:

```
/opt/openshell/bin/openshell-sandbox \
  --mode=process --log-level=debug \
  --policy-rules /etc/openshell/sandbox-policy.rego \
  --policy-data /etc/openshell/policy.yaml \
  -- bash /mnt/startup/startup.sh
```

### Key environment variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `OPENSHELL_ENDPOINT` | `https://openshell.openshell.svc.cluster.local:8080` | Gateway URL (mTLS) |
| `OPENSHELL_TLS_CA` | `/etc/openshell-tls/ca.crt` | CA cert for gateway TLS verification |
| `OPENSHELL_TLS_CERT` | `/etc/openshell-tls/tls.crt` | Client cert for mTLS handshake |
| `OPENSHELL_TLS_KEY` | `/etc/openshell-tls/tls.key` | Client key for mTLS handshake |
| `OPENSHELL_SANDBOX_UID/GID` | `1001310000` | Must match OpenShift SCC UID range |
| `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` | `admin` | Dashboard login user |
| `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` | from secret `agent-lens-auth` | Dashboard login password |
| `HERMES_DASHBOARD_HOST` | `0.0.0.0` | Bind to all interfaces |
| `HERMES_DASHBOARD_PORT` | `9119` | Dashboard port |
| `OPENAI_BASE_URL` | `http://llamastack-service.llamastack.svc:8321/v1` | LlamaStack inference |
| `LLAMASTACK_MODEL` | `gemini/models/gemini-2.5-flash` | Model identifier |
| `MLFLOW_MCP_URL` | `http://mlflow-mcp.redhat-ods-applications.svc.cluster.local:8080/mcp` | MLflow MCP |

### Security context

`runAsUser: 0`, `appArmorProfile: Unconfined`, capabilities `SYS_ADMIN, NET_ADMIN,
SYS_PTRACE, SYSLOG` -- all required by the OpenShell supervisor.

## Sandbox policy

### Landlock filesystem ([deploy/openshell/policy.yaml](deploy/openshell/policy.yaml))

| Access | Paths |
|--------|-------|
| Read-only | `/usr`, `/lib`, `/lib64`, `/bin`, `/sbin`, `/etc`, `/var/log`, `/proc`, `/dev/urandom`, `/opt/openshell` |
| Read-write | `/sandbox`, `/tmp`, `/dev/null`, `/dev/pts`, `/mnt`, `/run` |

`/dev/pts` is required for Hermes chat PTY allocation. Without it the UI shows
"out of pty devices".

### Network policies ([deploy/openshell/network-policies.yaml](deploy/openshell/network-policies.yaml))

| Direction | Target | Port |
|-----------|--------|------|
| Ingress | OpenShift ingress routers | 9119 |
| Egress | MLflow MCP (`redhat-ods-applications`) | 8080 |
| Egress | LlamaStack (`llamastack`) | 8321 |
| Egress | OpenShell gateway (`openshell`) | 8080 |
| Egress | HTTPS (any) | 443 |
| Egress | Cluster DNS (`openshift-dns`) | 53, 5353 |

### OPA Rego ([deploy/openshell/sandbox-policy.rego](deploy/openshell/sandbox-policy.rego))

Ships from NVIDIA. Evaluates network access decisions per-request when the supervisor
runs in `--mode=network,process`. In `--mode=process` (current), network policies are
informational only -- Landlock and seccomp provide the enforcement.

## Build pipeline

`make build-agent` triggers an OpenShift in-cluster build using the
[BuildConfig](deploy/buildconfig.yaml) and [ImageStream](deploy/imagestream.yaml)
in the `agent-lens` namespace:

1. `oc apply` creates/updates the ImageStream `agent-lens` and BuildConfig `agent-lens`
2. `oc start-build agent-lens --from-dir=agent-lens --follow` uploads the
   `agent-lens/` directory (Containerfile + config files) to the build pod
3. The build pod runs `buildah` with the [Containerfile](Containerfile) against the
   `python:3.13-slim` base image
4. The resulting image is pushed to the internal registry as
   `image-registry.openshift-image-registry.svc:5000/agent-lens/agent-lens:latest`
5. The Sandbox CR references this ImageStream tag with `imagePullPolicy: Always`

No local podman/docker is required. The build runs entirely in-cluster.

## Persistence (PVC)

The Sandbox CR includes a `volumeClaimTemplates` entry that creates a 5Gi PVC named
`workspace-agent-lens`:

```yaml
volumeClaimTemplates:
  - metadata:
      name: workspace
    spec:
      accessModes: [ReadWriteOnce]
      resources:
        requests:
          storage: 5Gi
```

The `workspace-init` init container copies `/sandbox` from the image to this PVC
on first boot (creates a `.workspace-initialized` marker file). On subsequent restarts,
the existing PVC content is used as-is, preserving:

- Hermes sessions (`/sandbox/.hermes/sessions/`)
- Memory store (`/sandbox/.hermes/memory/`)
- SQLite databases (`/sandbox/.hermes/db/`)
- Auto-learned skills (`/sandbox/.hermes/auto-skills/`)

To **reset state** completely, delete the PVC and the sandbox pod:

```bash
oc delete pvc workspace-agent-lens -n openshell
oc delete sandbox agent-lens -n openshell
make deploy-openshell
```

## Kustomize structure

[deploy/openshell/kustomization.yaml](deploy/openshell/kustomization.yaml) uses
`configMapGenerator` with `disableNameSuffixHash: true` to create ConfigMaps from
files outside the kustomization directory (skills, soul, config). Because skills
reference `../../skills/`, the build requires:

```bash
kustomize build --load-restrictor LoadRestrictionsNone agent-lens/deploy/openshell
```

The Makefile handles this automatically. If `kustomize` is not installed, it falls
back to `oc apply -k` (which does not support `--load-restrictor` and may fail if
files are outside the directory).

## Build, deploy, verify

```bash
# 1. Build image in-cluster (python:3.13-slim base, ~60s)
make build-agent

# 2. Deploy Sandbox + Service + Route + NetworkPolicy
make deploy-openshell

# 3. Check status
make status
```

### Verification checklist

```bash
# Pod is 1/1 Running
oc get pods -n openshell -l app=agent-lens

# Hermes v0.19.0+ in logs
oc logs agent-lens -n openshell -c agent | grep Hermes

# Dashboard returns login page
curl -sI https://$(oc get route agent-lens -n openshell -o jsonpath='{.spec.host}')

# Tail logs
make logs-openshell
```

Login: `admin` / password from `oc get secret agent-lens-auth -n openshell`.

## Teardown

```bash
make undeploy-openshell   # removes Sandbox, Service, Route, ConfigMaps, NetworkPolicy
```

The OpenShell gateway and Agent Sandbox Controller are left in place.

## Troubleshooting

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| `BuildPodEvicted` during `make build-agent` | OpenShell sandbox base image is 4GB, exceeds node ephemeral storage | Use `python:3.13-slim` as base (~150MB). Already done in current Containerfile. |
| hermes v0.15.2 installs instead of v0.19.0 | OpenShell base has Python 3.14; `hermes-agent>=0.16.0` declares `requires-python: <3.14`, so pip silently downgrades | Use Python 3.13 base. Already done in current Containerfile. |
| Supervisor kills `startup.sh` (exit 1) | Landlock + seccomp blocks runtime `pip install` (no network, no FS writes) | Bake all deps at build time. Never pip at pod start. |
| "out of pty devices" in chat UI | Landlock policy missing `/dev/pts` in read-write paths | Add `/dev/pts` to `policy.yaml` read_write list. Already done. |
| Gateway pod fails SCC validation | OpenShift `restricted-v2` rejects Helm defaults `runAsUser: 1000`, `fsGroup: 1000` | `--set podSecurityContext.fsGroup=null --set securityContext.runAsUser=null` |
| Service 503 / no endpoints | Service selector doesn't match pod labels | Ensure `podTemplate.metadata.labels` includes `app: agent-lens` and Service selector matches |
| Dashboard "Refusing to bind to 0.0.0.0" | Hermes blocks non-loopback bind without auth provider | Add `--insecure` flag to `hermes dashboard` command in `startup.sh` |
| `SIGPIPE` crash on `hermes --version \| head -1` | Under `set -o pipefail`, broken pipe returns non-zero | Use `hermes --version 2>&1 \|\| true` without pipe |

### FIPS clusters

On FIPS-enabled clusters, `curl` inside the sandbox may fail with
`curl: (35) Insufficient randomness` after adding egress policy. This is a known
issue with the base container image's OpenSSL build on FIPS nodes.

### OpenShell CLI quick reference

```bash
# Create a sandbox interactively
openshell sandbox create --name my-sandbox

# Open a terminal into the sandbox
openshell term

# Add egress policy for a specific endpoint
openshell policy update my-sandbox \
  --add-endpoint github.com:443:read-only:rest:enforce \
  --binary /usr/bin/curl --wait
```

### Follow-up topics

- [Access control -- configure IDP for gateway authentication](https://docs.nvidia.com/openshell/latest/kubernetes/access-control)
- [Ingress -- expose gateway via Route/Ingress instead of port-forward](https://docs.nvidia.com/openshell/latest/kubernetes/ingress)
- [Gateway authentication modes (mTLS vs OIDC)](https://docs.nvidia.com/openshell/latest/reference/gateway-auth)

## Manifests reference

```
deploy/openshell/
├── kustomization.yaml      # Kustomize entry point (namespace: openshell)
├── sandbox.yaml            # Sandbox CR (pod template, init containers, env vars)
├── services.yaml           # Service + Route
├── network-policies.yaml   # Kubernetes NetworkPolicy
├── policy.yaml             # Landlock filesystem + network policy data
├── sandbox-policy.rego     # OPA Rego rules (from NVIDIA)
└── startup.sh              # Pod entrypoint (copies skills, patches config, starts Hermes)
```

See also: [../docs/limitations.md](../docs/limitations.md),
[../docs/enterprise-readiness.md](../docs/enterprise-readiness.md),
[../docs/operator-mcp.md](../docs/operator-mcp.md).
