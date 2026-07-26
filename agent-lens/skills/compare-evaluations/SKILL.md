---
name: "compare-evaluations"
description: "Compare evaluation results across agent versions, time periods, or scorer profiles. Use when asked to diff quality between versions, track improvement after fixes, or compare agents head-to-head."
---

# Compare Evaluations

Side-by-side comparison of evaluation results across versions, time periods, or agents.

## When to Use

- "Compare v1.2 vs v1.3 of the outreach agent"
- "Did the fix improve quality?"
- "Compare agent A vs agent B"
- "Show me before/after the prompt change"
- "How has quality trended across the last 3 evaluations?"

## Strategy

### Step 1: Identify comparison targets

Determine what is being compared:
- **Version diff** — same agent, different versions (most common)
- **Before/after** — same agent, pre/post-fix evaluation runs
- **Agent vs agent** — two different agents, same scorer profile
- **Temporal** — same agent evaluated at different points

### Step 2: Fetch evaluation runs

1. `mcp_mlflow_list_runs` — find evaluation runs for the target experiment(s)
2. `mcp_mlflow_describe_run` — get detailed metrics from each run
3. Extract scorer pass rates, error rates, sample sizes from run metrics/tags

### Step 3: Align metrics for comparison

Match scorer dimensions across runs. Flag when:
- Different scorer profiles were used (not directly comparable)
- Sample sizes differ significantly
- One run had scorer errors the other did not

### Step 4: Present comparison

## Output Format

```
## Evaluation Comparison
### Agent: [name] | [version_a] vs [version_b]

### Pass Rates
| Scorer | [version_a] | [version_b] | Delta | Verdict |
|--------|------------|------------|-------|---------|
| RelevanceToQuery | 78% | 92% | +14% | IMPROVED |
| RetrievalGroundedness | 80% | 85% | +5% | IMPROVED |
| ToolCallCorrectness | N/A | 88% | — | NEW |

### Operational
| Metric | [version_a] | [version_b] | Delta |
|--------|------------|------------|-------|
| Error rate | 8% | 2% | -6% |
| Avg latency | 2,100ms | 1,800ms | -300ms |
| Traces evaluated | 200 | 200 | — |

### Qualification Status
- **[version_a]**: NOT QUALIFIED (RelevanceToQuery below 80%)
- **[version_b]**: QUALIFIED (all scorers ≥ 80%, error rate < 5%)

### Recommendation
[version_b] shows meaningful improvement across all measured dimensions.
Ready for production qualification.
```

## Comparison Validity Rules

- Warn if scorer profiles differ (apples-to-oranges)
- Warn if sample sizes differ by more than 2x
- Warn if evaluation was run more than 30 days apart (agent behavior may have drifted)
- Delta is always `version_b - version_a` (positive = improvement)

## Constraints

- All data from MLflow MCP — never `import mlflow`
- Present side-by-side, not narrative — let the numbers speak
- Always include sample sizes so the user can judge statistical significance
- Cap at 5 comparison targets per request
