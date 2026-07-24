---
name: "compare-agents"
description: "Compare two experiments or runs side-by-side on key metrics. Use when asked to compare agent versions, time periods, or different agents against each other."
---

# Compare Agents

Side-by-side comparison of agent performance across runs, versions, or time periods.

## Strategy

1. Identify what to compare:
   - Two specific runs — use `mcp_mlflow_compare_runs` directly
   - Two experiments — call `mcp_mlflow_search_runs` on each, then compare latest runs
   - Before/after — search runs with time-based ordering
2. Get comparison data — use `mcp_mlflow_compare_runs` with run_ids and metric_keys
3. Analyze deltas and determine which is better and why

## Common Comparison Scenarios

| User asks | Strategy |
|-----------|----------|
| "Compare last two evals" | Search runs, pick latest 2, compare |
| "Is the agent better this week?" | Search runs by time, compare windows |
| "Compare agent A vs agent B" | List experiments, search runs in each |
| "Before/after the prompt change" | Search runs around the change date |

## When to Use Code Execution

Use code execution when:
- Comparing more than 2 runs (matrix comparison)
- Computing statistical significance of differences
- Aggregating metrics across multiple runs per time window

## Output Format

```
## Comparison: [Run A name] vs [Run B name]

| Metric | Run A | Run B | Delta | Winner |
|--------|-------|-------|-------|--------|
| Relevance | X.X | Y.Y | +/-Z.Z | A/B |
| Faithfulness | X.X | Y.Y | +/-Z.Z | A/B |
| Correctness | X.X | Y.Y | +/-Z.Z | A/B |
| Latency | Xs | Ys | +/-Zs | A/B |

### Verdict
[Which is better overall and why — 1-2 sentences]

### Key Differences
- [What improved]
- [What regressed]

### Recommendation
[Keep new version / Roll back / Investigate further]
```

## Analysis Guidelines

- Flag any metric that moved more than 0.5 points as significant
- Note sample size — small samples mean unreliable comparisons
- If latency increased but quality improved, frame as a tradeoff not a regression
- Always check if one run had significantly more errors
