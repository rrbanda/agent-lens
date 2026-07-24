.PHONY: help deploy-agent deploy-all undeploy secret eval logs-agent status check-mcp build-agent

NAMESPACE ?= agent-lens
MCP_URL ?= http://mlflow-mcp.redhat-ods-applications.svc.cluster.local:8080/mcp
AGENT_IMAGE ?= quay.io/rrbanda/agent-lens:v3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

secret: ## Create LLM + dashboard/API secrets (interactive)
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
	@echo "✓ Secrets agent-lens-llm-key and agent-lens-auth upserted in $(NAMESPACE)"
	@echo "  Reminder: official MLflow MCP (mlflow-mcp) must already be installed."

build-agent: ## Build immutable Hermes image (podman/docker)
	podman build -t $(AGENT_IMAGE) -f agent-lens/Containerfile agent-lens/ \
		|| docker build -t $(AGENT_IMAGE) -f agent-lens/Containerfile agent-lens/
	@echo "✓ Built $(AGENT_IMAGE)"
	@echo "  Push to your registry, then: oc set image deploy/agent-lens hermes=$(AGENT_IMAGE) -n $(NAMESPACE)"
	@echo "  And: oc set env deploy/agent-lens BOOTSTRAP_DEPS=0 -n $(NAMESPACE)"

deploy-agent: ## Deploy the Agent Lens observability agent
	@echo "Deploying Agent Lens to $(NAMESPACE)..."
	oc apply -k agent-lens/deploy/ --server-side --force-conflicts 2>/dev/null \
		|| oc apply -k agent-lens/deploy/
	@echo "✓ Agent Lens deployed"
	@echo "  MCP prerequisite: $(MCP_URL)"
	@echo "  See docs/operator-mcp.md and docs/enterprise-readiness.md"

deploy-all: secret deploy-agent ## Secrets + Agent Lens (MCP is a prerequisite)
	@echo ""
	@echo "═══════════════════════════════════════════════"
	@echo "  Agent Lens deployed successfully!"
	@echo "  Dashboard: $$(oc get route agent-lens -n $(NAMESPACE) -o jsonpath='{.spec.host}')"
	@echo "  MCP: upstream mlflow-mcp (not installed by this Makefile)"
	@echo "  Next: docs/first-trace.md then docs/demo-script.md"
	@echo "═══════════════════════════════════════════════"

undeploy: ## Remove Agent Lens resources
	oc delete -k agent-lens/deploy/ --ignore-not-found
	oc delete namespace $(NAMESPACE) --ignore-not-found
	@echo "✓ Agent Lens removed"

eval: ## Run an evaluation against a target agent
	@if [ -z "$(AGENT_API_URL)" ]; then echo "ERROR: Set AGENT_API_URL"; exit 1; fi
	@if [ -z "$(AGENT_API_KEY)" ]; then echo "ERROR: Set AGENT_API_KEY"; exit 1; fi
	python instrumentation/eval_agent.py \
		--experiment-name "$(MLFLOW_EXPERIMENT_NAME)" \
		--workspace "$(MLFLOW_WORKSPACE)"

logs-agent: ## Tail Agent Lens logs
	oc logs -f deploy/agent-lens -n $(NAMESPACE)

check-mcp: ## Compare config allowlist to live MCP tools/list
	MCP_URL=$(MCP_URL) ./scripts/check_mcp_contract.sh

status: ## Show deployment status
	@echo "=== Official MLflow MCP ==="
	@oc get pods -l app=mlflow-mcp -n redhat-ods-applications 2>/dev/null || echo "  Not found (check RHOAI / mlflow-mcp deploy)"
	@echo ""
	@echo "=== Agent Lens ==="
	@oc get pods -l app=agent-lens -n $(NAMESPACE) 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Secrets ==="
	@oc get secret agent-lens-llm-key agent-lens-auth -n $(NAMESPACE) 2>/dev/null || echo "  Missing — run make secret"
	@echo ""
	@echo "=== Route ==="
	@oc get route agent-lens -n $(NAMESPACE) -o jsonpath='  https://{.spec.host}\n' 2>/dev/null || echo "  No route"
