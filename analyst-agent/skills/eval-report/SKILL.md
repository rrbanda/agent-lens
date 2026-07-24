---
name: "eval-report"
description: "Pull evaluation metrics from MLflow runs and format a quality report with trends. Use when asked about agent quality scores, evaluation results, or performance over time."
---

# Evaluation Report

Generate quality reports from MLflow evaluation runs that score agent outputs.

## Strategy

1. Find evaluation runs — call `mcp_mlflow_search_runs` with experiment_id, filter for eval-tagged runs
2. Get detailed metrics — call `mcp_mlflow_get_run` for each eval run
3. Track trends — call `mcp_mlflow_get_metric_history` for key metrics
4. Synthesize into a quality assessment with actionable recommendations

## Key Metrics to Look For

| Metric | Meaning | Good | Fair | Poor |
|--------|---------|------|------|------|
| relevance_mean | Output addresses the request | >= 4.0 | >= 3.0 | < 3.0 |
| faithfulness_mean | Grounded in provided context | >= 4.0 | >= 3.0 | < 3.0 |
| correctness_mean | Factually accurate | >= 4.0 | >= 3.0 | < 3.0 |
| token_count_mean | Efficiency | < 1500 | < 3000 | > 3000 |

## When to Use Code Execution

Use code execution when:
- Comparing metrics across multiple eval runs (trend analysis)
- Computing statistical significance between runs
- Generating a time-series view of quality evolution

## Output Format

```
## Quality Report: [agent name] (Experiment [id])
### Evaluation Run: [run_name] — [timestamp]

| Dimension | Score (1-5) | Rating | Trend |
|-----------|-------------|--------|-------|
| Relevance | X.X | Good/Fair/Poor | up/down/stable |
| Faithfulness | X.X | Good/Fair/Poor | up/down/stable |
| Correctness | X.X | Good/Fair/Poor | up/down/stable |
| **Overall** | **X.X** | **Rating** | |

### Assessment
[1-2 sentence quality summary]

### Recommendations
- [Specific action based on lowest-scoring dimension]
- [Data-backed suggestion for improvement]
```
