# Security Policy

## Supported Versions

| Version | Milestone | Supported |
|---------|-----------|-----------|
| M2.x | Production Hardening | :white_check_mark: Active development |
| M1.x | MVP Pilot | :white_check_mark: Security fixes only |
| M0.x | Upstream Foundation | :x: No longer supported |

Agent Lens follows milestone-based releases. Only the current and immediately
previous milestones receive security fixes.

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, report vulnerabilities through one of these channels:

1. **GitHub Private Security Advisory** (preferred):
   Go to **Security → Advisories → New draft advisory** at
   [github.com/rrbanda/agent-lens/security/advisories](https://github.com/rrbanda/agent-lens/security/advisories)

2. **Email**: Send details to the repository maintainers listed in [CODEOWNERS](.github/CODEOWNERS).

Please include:

- Description of the vulnerability
- Steps to reproduce
- Affected component (Hermes Sandbox, Gateway, instrumentation, deploy manifests)
- Severity estimate (Critical / High / Medium / Low)
- Any suggested fix

We will acknowledge receipt within **48 hours** and provide an initial assessment
within **7 business days**.

---

## Security Model

Agent Lens runs as an **OpenShell Sandbox** on Kubernetes with multiple layers of isolation.

### Sandbox Isolation

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| **Landlock** | Linux Security Module | Restricts filesystem access to workspace-only |
| **seccomp** | System call filtering | Blocks dangerous syscalls |
| **NetworkPolicy** | Kubernetes-native | Limits egress to MLflow MCP endpoint only |
| **Pod Security** | Pod Security Standards / SCC | Non-root UID, read-only root filesystem, dropped capabilities |
| **Immutable image** | Container best practice | No package installs at runtime |

### Data Flow Boundaries

```
  External User
       │
       ▼
  OAuth Proxy (SSO / OIDC)     ← authentication boundary
       │
       ▼
  Hermes Agent (Sandbox)        ← Landlock + seccomp boundary
       │
       ▼ (MCP only)
  MLflow MCP Server             ← NetworkPolicy boundary
       │
       ▼
  MLflow Tracking Server        ← cluster-managed
```

Agent Lens **never** accesses MLflow directly — all data flows through the official
MLflow MCP server. The sandbox cannot `import mlflow` or make direct SDK calls.

### Authentication

| Component | Auth Mechanism | Status |
|-----------|---------------|--------|
| Dashboard / Chat | OAuth Proxy (SSO / OIDC) | M2 |
| Gateway REST API | API key (scrypt-hashed) | M2 |
| Gateway MCP | Same as Gateway REST | M2 |
| MLflow MCP | Cluster-internal (NetworkPolicy) | M1 |

### Audit Trail Integrity

The governance audit trail (M2) uses:

- **Append-only JSONL** — no update or delete operations
- **SHA-256 hash chain** — each entry references the hash of the previous entry
- **Actor identity** — every decision record includes the authenticated user identity
- **Tamper evidence** — hash chain breakage indicates modification

---

## Scope

### In Scope

Vulnerabilities in the following are within scope for security reports:

- Agent Lens Hermes skills (`agent-lens/skills/`)
- Agent Lens soul / config (`agent-lens/soul.md`, `agent-lens/config.yaml`)
- Gateway API (`gateway/`)
- Deployment manifests (`agent-lens/deploy/`)
- Instrumentation helpers (`instrumentation/`)
- Container image (`agent-lens/Containerfile`)
- CI/CD pipeline definitions (`.github/workflows/`)

### Out of Scope

The following are **not** Agent Lens security issues — report them to their
respective projects:

| Component | Where to Report |
|-----------|----------------|
| MLflow vulnerabilities | [mlflow/mlflow](https://github.com/mlflow/mlflow/security) |
| MLflow MCP server | [mlflow/mlflow](https://github.com/mlflow/mlflow/security) |
| Hermes Agent framework | Hermes project security process |
| OpenShell runtime | OpenShell project security process |
| LlamaStack / inference | LlamaStack project security process |
| Kubernetes platform (OpenShift, EKS, GKE, etc.) | Platform vendor's security process |

---

## Security Best Practices for Contributors

1. **Never commit credentials** — use K8s Secrets with placeholder templates
2. **Never `import mlflow`** in sandbox code — all access goes through MCP
3. **Never add `pip install`** to runtime — the container image is immutable
4. **Always use NetworkPolicy** — restrict egress to known endpoints
5. **Always set security contexts** — non-root, read-only rootfs, drop all capabilities
6. **Review skill MCP tool usage** — skills must only reference allowlisted tools

See [CONTRIBUTING.md](CONTRIBUTING.md) and [DESIGN.md](DESIGN.md) for architectural
constraints that enforce these practices.
