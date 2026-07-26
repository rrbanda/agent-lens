.PHONY: help secret secret-openshell build-agent deploy-agent \
	deploy-openshell deploy-all undeploy undeploy-openshell scale-down-legacy \
	eval logs-agent logs-openshell status check-mcp \
	test test-unit test-integration mlflow-start mlflow-stop seed-data

NAMESPACE ?= agent-lens
OPENSHELL_NS ?= openshell
MCP_URL ?= http://mlflow-mcp.redhat-ods-applications.svc.cluster.local:8080/mcp
AGENT_IMAGE ?= quay.io/rrbanda/agent-lens:v3
MLFLOW_PORT ?= 5555
MLFLOW_TRACKING_URI ?= http://127.0.0.1:$(MLFLOW_PORT)
VENV ?= .venv

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

secret: ## Create LLM + dashboard/API secrets in agent-lens (legacy Deployment rollback)
	@read -p "Enter your Gemini API key: " KEY && \
	oc create secret generic agent-lens-llm-key \
		--from-literal=api-key="$$KEY" \
		-n $(NAMESPACE) --dry-run=client -o yaml | oc apply -f -
	@read -p "Enter dashboard password: " DASH_PW && \
	read -p "Enter API server key: " API_KEY && \
	oc create secret generic agent-lens-auth \
		--from-literal=dashboard-password="$$DASH_PW" \
		--from-literal=api-server-key="$$API_KEY" \
		-n $(NAMESPACE) --dry-run=client -o yaml | oc apply -f -
	@echo "✓ Secrets upserted in $(NAMESPACE) (legacy path)"

secret-openshell: ## Create agent-lens-auth in openshell (dashboard password + LLM API key)
	@if [ -n "$$DASH_PW" ] && [ -n "$$API_KEY" ]; then \
		oc create secret generic agent-lens-auth \
			--from-literal=dashboard-password="$$DASH_PW" \
			--from-literal=api-server-key="$$API_KEY" \
			--from-literal=llm-api-key="$${LLM_API_KEY:-not-needed}" \
			-n $(OPENSHELL_NS) --dry-run=client -o yaml | oc apply -f - ; \
	else \
		read -p "Enter dashboard password: " DASH_PW && \
		read -p "Enter API server key: " API_KEY && \
		read -p "Enter LLM API key (Gemini/OpenAI/etc, or 'not-needed' for local): " LLM_API_KEY && \
		oc create secret generic agent-lens-auth \
			--from-literal=dashboard-password="$$DASH_PW" \
			--from-literal=api-server-key="$$API_KEY" \
			--from-literal=llm-api-key="$$LLM_API_KEY" \
			-n $(OPENSHELL_NS) --dry-run=client -o yaml | oc apply -f - ; \
	fi
	@echo "✓ Secret agent-lens-auth upserted in $(OPENSHELL_NS)"

build-agent: ## Build OpenShell-base Hermes image in-cluster (no local podman/docker required)
	@echo "Ensuring ImageStream + BuildConfig in $(NAMESPACE)..."
	oc apply -f agent-lens/deploy/namespace.yaml
	oc apply -f agent-lens/deploy/imagestream.yaml -n $(NAMESPACE)
	oc apply -f agent-lens/deploy/buildconfig.yaml -n $(NAMESPACE)
	@echo "Ensuring OpenShell sandbox base ImageStream..."
	@oc get istag openshell-sandbox-base:latest -n $(NAMESPACE) >/dev/null 2>&1 || \
		oc import-image openshell-sandbox-base:latest \
			--from=ghcr.io/nvidia/openshell-community/sandboxes/base:latest \
			--confirm -n $(NAMESPACE)
	@echo "Cleaning old failed build pods to free ephemeral storage..."
	@oc delete builds -n $(NAMESPACE) -l buildconfig=agent-lens --field-selector=status.phase=Failed --ignore-not-found >/dev/null 2>&1 || true
	@echo "Starting in-cluster binary build (pinned to high-ephemeral node)..."
	oc start-build agent-lens -n $(NAMESPACE) --from-dir=agent-lens --follow --wait
	@echo "✓ ImageStreamTag agent-lens:latest updated"
	@echo "  Sandbox uses: image-registry.../agent-lens/agent-lens:latest"

# No local podman/docker required. If make build-agent hits BuildPodEvicted, the
# OpenShell overlay already defaults to quay.io/rbrhssa/o-reach-hermes:latest
# (pull via openshell/quay-push-secret). Rebuild Agent Lens Containerfile later
# when cluster ephemeral-storage allows, then point Sandbox image at the ImageStream.

deploy-openshell: ## Deploy Agent Lens Sandbox into openshell (production path)
	@echo "Checking OpenShell platform prerequisites..."
	@oc get sa openshell-sandbox -n $(OPENSHELL_NS) >/dev/null \
		|| { echo "ERROR: SA openshell-sandbox missing in $(OPENSHELL_NS)"; exit 1; }
	@oc get secret agent-lens-auth -n $(OPENSHELL_NS) >/dev/null \
		|| { echo "ERROR: secret agent-lens-auth missing — run: make secret-openshell"; exit 1; }
	@oc get secret openshell-client-tls -n $(OPENSHELL_NS) >/dev/null \
		|| { echo "ERROR: openshell-client-tls missing — gateway not installed or TLS not generated"; exit 1; }
	@echo "Deploying OpenShell Sandbox to $(OPENSHELL_NS)..."
	@oc delete job agent-lens-configure-inference -n $(OPENSHELL_NS) --ignore-not-found >/dev/null 2>&1 || true
	@if [ -x /tmp/kustomize ]; then K=/tmp/kustomize; \
	elif command -v kustomize >/dev/null; then K=kustomize; \
	else K=; fi; \
	if [ -n "$$K" ]; then \
		$$K build --load-restrictor LoadRestrictionsNone agent-lens/deploy/openshell | oc apply -f - ; \
	else \
		oc apply -k agent-lens/deploy/openshell/ ; \
	fi
	@echo "✓ OpenShell Sandbox applied"
	@echo "  MCP: $(MCP_URL)"
	@echo "  Route: $$(oc get route agent-lens -n $(OPENSHELL_NS) -o jsonpath='{.spec.host}' 2>/dev/null || echo pending)"

deploy-agent: ## DEPRECATED — plain Deployment in agent-lens (rollback only)
	@echo "WARNING: deploy-agent is deprecated. Prefer: make build-agent && make deploy-openshell"
	@if command -v kustomize >/dev/null; then \
		kustomize build --load-restrictor LoadRestrictionsNone agent-lens/deploy | oc apply -f - ; \
	else \
		oc apply -k agent-lens/deploy/ ; \
	fi

deploy-all: deploy-openshell ## Deploy OpenShell Sandbox (optional: make build-agent first)
	@echo ""
	@echo "═══════════════════════════════════════════════"
	@echo "  Agent Lens on OpenShell (openshell ns)"
	@echo "  Dashboard: https://$$(oc get route agent-lens -n $(OPENSHELL_NS) -o jsonpath='{.spec.host}')"
	@echo "  MCP: upstream mlflow-mcp (prerequisite)"
	@echo "  LLM: Any OpenAI-compatible API (set OPENAI_BASE_URL + OPENAI_API_KEY)"
	@echo "  Image: quay OpenShell Hermes (or ImageStream after make build-agent)"
	@echo "═══════════════════════════════════════════════"

scale-down-legacy: ## Scale down legacy Deployment in agent-lens after OpenShell smoke
	oc scale deploy/agent-lens -n $(NAMESPACE) --replicas=0 2>/dev/null || true
	@echo "✓ Legacy Deployment scaled to 0 (ImageStream/BuildConfig kept)"

undeploy-openshell: ## Remove OpenShell Sandbox resources (keeps platform)
	@if [ -x /tmp/kustomize ]; then K=/tmp/kustomize; \
	elif command -v kustomize >/dev/null; then K=kustomize; \
	else K=; fi; \
	if [ -n "$$K" ]; then \
		$$K build --load-restrictor LoadRestrictionsNone agent-lens/deploy/openshell | oc delete -f - --ignore-not-found ; \
	else \
		oc delete -k agent-lens/deploy/openshell/ --ignore-not-found ; \
	fi
	@echo "✓ OpenShell Agent Lens resources removed"

undeploy: ## Remove legacy agent-lens Deployment stack (optional namespace delete)
	oc delete -k agent-lens/deploy/ --ignore-not-found
	@echo "✓ Legacy deploy removed (namespace $(NAMESPACE) kept for ImageStream/builds)"

eval: ## Run an evaluation against a target agent
	@if [ -z "$(AGENT_API_URL)" ]; then echo "ERROR: Set AGENT_API_URL"; exit 1; fi
	@if [ -z "$(AGENT_API_KEY)" ]; then echo "ERROR: Set AGENT_API_KEY"; exit 1; fi
	python instrumentation/eval_agent.py \
		--experiment-name "$(MLFLOW_EXPERIMENT_NAME)" \
		--workspace "$(MLFLOW_WORKSPACE)"

logs-agent: ## Tail legacy Deployment logs
	oc logs -f deploy/agent-lens -n $(NAMESPACE)

logs-openshell: ## Tail OpenShell Sandbox agent logs
	@POD=$$(oc get pods -n $(OPENSHELL_NS) -l app=agent-lens -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
	  POD=$$(oc get pods -n $(OPENSHELL_NS) -l agents.x-k8s.io/sandbox-name=agent-lens -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	fi; \
	test -n "$$POD" || { echo "No agent-lens sandbox pod"; exit 1; }; \
	oc logs -f -n $(OPENSHELL_NS) "$$POD" -c agent

check-mcp: ## Compare config allowlist to live MCP tools/list
	MCP_URL=$(MCP_URL) ./scripts/check_mcp_contract.sh

# ── Testing ───────────────────────────────────────────────────────────────────

test: test-unit ## Run all tests (unit only; use test-integration for MCP tests)

test-unit: ## Run unit tests (no MLflow server required)
	$(VENV)/bin/python -m pytest tests/test_skill_alignment.py -v

test-integration: ## Run integration tests against local MLflow + MCP
	MLFLOW_TRACKING_URI=$(MLFLOW_TRACKING_URI) \
		$(VENV)/bin/python -m pytest tests/test_mcp_integration.py -v -m integration

mlflow-start: ## Start local MLflow server for development
	@mkdir -p .mlflow-test
	@echo "Starting MLflow server on port $(MLFLOW_PORT)..."
	$(VENV)/bin/mlflow server \
		--host 127.0.0.1 --port $(MLFLOW_PORT) \
		--backend-store-uri sqlite:///.mlflow-test/mlflow.db \
		--default-artifact-root .mlflow-test/artifacts &
	@sleep 3
	@echo "✓ MLflow running at $(MLFLOW_TRACKING_URI)"

mlflow-stop: ## Stop local MLflow server
	@pkill -f "mlflow server.*$(MLFLOW_PORT)" 2>/dev/null || true
	@echo "✓ MLflow stopped"

seed-data: ## Seed local MLflow with test data (requires mlflow-start)
	MLFLOW_TRACKING_URI=$(MLFLOW_TRACKING_URI) \
		$(VENV)/bin/python tests/seed_mlflow_data.py

dev-setup: ## Set up local dev environment (venv + deps)
	python3.13 -m venv $(VENV) || python3.12 -m venv $(VENV) || python3.11 -m venv $(VENV)
	$(VENV)/bin/pip install --quiet -e ".[dev]"
	@echo "✓ Dev environment ready. Activate: source $(VENV)/bin/activate"

status: ## Show MCP + OpenShell Sandbox + legacy status
	@echo "=== Official MLflow MCP ==="
	@oc get pods -l app=mlflow-mcp -n redhat-ods-applications 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "=== OpenShell Sandbox (production) ==="
	@oc get sandbox agent-lens -n $(OPENSHELL_NS) 2>/dev/null || echo "  Sandbox not deployed"
	@oc get pods -n $(OPENSHELL_NS) -l app=agent-lens 2>/dev/null || true
	@oc get route agent-lens -n $(OPENSHELL_NS) -o jsonpath='  https://{.spec.host}\n' 2>/dev/null || echo "  No openshell route"
	@echo ""
	@echo "=== Legacy Deployment (rollback) ==="
	@oc get deploy,pods -l app=agent-lens -n $(NAMESPACE) 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Secrets ==="
	@oc get secret agent-lens-auth -n $(OPENSHELL_NS) 2>/dev/null || echo "  Missing openshell auth — make secret-openshell"
	@oc get secret agent-lens-auth -n $(NAMESPACE) 2>/dev/null || true
