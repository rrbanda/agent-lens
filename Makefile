.PHONY: help deploy-mcp deploy-agent deploy-all undeploy secret build-mcp eval

NAMESPACE ?= agent-lens
MCP_NAMESPACE ?= $(NAMESPACE)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

secret: ## Create the LLM API key secret (interactive)
	@read -p "Enter your Gemini API key: " KEY && \
	oc create secret generic agent-lens-llm-key \
		--from-literal=api-key="$$KEY" \
		-n $(NAMESPACE) --dry-run=client -o yaml | oc apply -f -
	@echo "✓ Secret created in namespace $(NAMESPACE)"

deploy-mcp: ## Deploy the MLflow MCP Server
	@echo "Deploying MLflow MCP Server to $(MCP_NAMESPACE)..."
	oc apply -k mcp-server/deploy/
	@echo "✓ MCP Server deployed"

deploy-agent: ## Deploy the Agent Lens observability agent
	@echo "Deploying Agent Lens to $(NAMESPACE)..."
	oc apply -k analyst-agent/deploy/
	@echo "✓ Agent Lens deployed"

deploy-all: secret deploy-mcp deploy-agent ## Deploy everything (creates namespace + secret + services)
	@echo ""
	@echo "═══════════════════════════════════════════════"
	@echo "  Agent Lens deployed successfully!"
	@echo "  Dashboard: $$(oc get route agent-lens -n $(NAMESPACE) -o jsonpath='{.spec.host}')"
	@echo "  Login: admin / openshift (default)"
	@echo "═══════════════════════════════════════════════"

undeploy: ## Remove all Agent Lens resources
	oc delete -k analyst-agent/deploy/ --ignore-not-found
	oc delete -k mcp-server/deploy/ --ignore-not-found
	oc delete namespace $(NAMESPACE) --ignore-not-found
	@echo "✓ Agent Lens removed"

build-mcp: ## Build the MCP server container image
	podman build -t agent-lens-mcp:latest -f mcp-server/Containerfile mcp-server/

eval: ## Run an evaluation against a target agent
	@if [ -z "$(AGENT_API_URL)" ]; then echo "ERROR: Set AGENT_API_URL"; exit 1; fi
	@if [ -z "$(AGENT_API_KEY)" ]; then echo "ERROR: Set AGENT_API_KEY"; exit 1; fi
	python instrumentation/eval_agent.py \
		--experiment-name "$(MLFLOW_EXPERIMENT_NAME)" \
		--workspace "$(MLFLOW_WORKSPACE)"

logs-mcp: ## Tail MLflow MCP server logs
	oc logs -f deploy/mlflow-mcp-server -n $(MCP_NAMESPACE)

logs-agent: ## Tail Agent Lens logs
	oc logs -f deploy/agent-lens -n $(NAMESPACE)

status: ## Show deployment status
	@echo "=== MCP Server ==="
	@oc get pods -l app=mlflow-mcp-server -n $(MCP_NAMESPACE) 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Agent Lens ==="
	@oc get pods -l app=agent-lens -n $(NAMESPACE) 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "=== Route ==="
	@oc get route agent-lens -n $(NAMESPACE) -o jsonpath='  https://{.spec.host}\n' 2>/dev/null || echo "  No route"
