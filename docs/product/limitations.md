# Known limitations

Agent Lens uses **upstream official MLflow MCP** only. Capabilities that previously
existed (or were marketed) via a custom FastMCP server are **not** product APIs today.

## Capability contract

| Marketing phrase | Reality today | Roadmap |
|------------------|---------------|---------|
| Quality **gate** / block deploy | Skill compares **pass rates** (≥80% yes/no scorers) and returns a chat verdict | Enforceable CI webhook: [#18](https://github.com/rrbanda/agent-lens/issues/18) |
| Regression **dataset** | `log_expectation` + tags (`regression=true`, `dataset=…`) | Durable GenAI datasets via MLflow UI/SDK or upstream MCP tools |
| **Review queue** | `search_traces` heuristics (errors / recent) | Upstream queue tool or smarter skill sampling |
| Fleet **health summary** | Cap ≤20 experiments; N MCP calls (`search_experiments` + `search_traces` / `list_runs`) | Upstream aggregate tool or caching |
| Custom MCP server | **Removed** from this repo | Do not reintroduce as default path |

## What Agent Lens will not do

- Install or operate MLflow / official MCP for you (`make deploy-all` is Hermes only)
- Give the Hermes sandbox a ServiceAccount to call MLflow directly — **never** `import mlflow` in code execution
- Guarantee scorers/judges without a configured LLM behind MLflow GenAI evaluation
- Instrument non-Python or non-OpenAI-compatible stacks via `usercustomize.py` alone

## Tool naming

Hermes exposes official tools as `mcp_mlflow_<name>`. The allowlist lives in
[`agent-lens/config.yaml`](../agent-lens/config.yaml). If upstream renames a tool,
update the allowlist and skills together, then run:

```bash
pytest tests/test_skill_alignment.py -v
./scripts/check_mcp_contract.sh   # against a live MCP endpoint when available
```

## Demo implications

- Empty experiments → Observatory rows show **INACTIVE** (not a cluster outage)
- “Can this agent be deployed?” → advisory qualification, not a pipeline block
- “Add to regression dataset” → expectation + tags; promote to a real dataset offline if required
