---
name: "cost-quality"
description: "Analyze cost vs quality tradeoffs across evaluation runs. Use when asked to compare costs, find the best model, optimize spending, or evaluate cost-efficiency of an agent."
---

# Cost-Quality Tradeoff Analysis

Compare quality and cost across evaluation runs to find the optimal tradeoff via **upstream official MLflow MCP**.
Based on [MLflow Cookbook: Cost-Quality Tradeoff Analysis Across LLM Providers](https://mlflow.org/cookbook/cost-quality-tradeoff/).

Helps platform engineers answer: "Which configuration gives the best quality for the budget?"

## When to Use

- "Compare quality vs cost across my evaluation runs"
- "Which model gives the best quality for the support agent?"
- "Show me the cost-quality tradeoff for the RAG agent"
- "Is GPT-4o worth the extra cost over GPT-4o-mini?"
- "How much does each qualified trace cost?"
- "Optimize spending on the financial advisor agent"

## Strategy

### Step 1: Identify Agent and Scope

1. `mcp_mlflow_search_experiments` — find target experiment
2. Confirm with user: compare across models? across time? across configurations?

### Step 2: Gather Evaluation Runs

Call `mcp_mlflow_list_runs` for the experiment:
- Filter for evaluation runs (look for runs with scorer metrics like `correctness/mean`, `completeness/mean`)
- Retrieve at least 2 runs for comparison (ideally 3-5)

For each run, call `mcp_mlflow_describe_run` to extract:
- **Quality metrics**: The cookbook uses `Correctness` and `Completeness` as primary scorers.
  Look for `correctness/mean` and `completeness/mean` in run metrics.
- **Run metadata**: model used, timestamp, parameters, tags
- **Run name**: often encodes the model/configuration being tested (e.g., "gpt-4o-mini", "gpt-4o")

### Step 3: Gather Cost Data from Traces

The [MLflow Cost-Quality Cookbook](https://mlflow.org/cookbook/cost-quality-tradeoff/) shows that
token usage is automatically captured when `mlflow.openai.autolog()` is enabled and stored
in `trace.info.token_usage`.

For each run, call `mcp_mlflow_search_traces` (filter by `run_id` if possible):

**Token usage extraction** (from the cookbook's `sum_token_usage` pattern):
- Look for `token_usage` in trace info: `trace.info.token_usage.input_tokens`, `.output_tokens`
- If not in `token_usage`, check `trace.info.request_metadata["mlflow.trace.tokenUsage"]`
  (JSON string with `input_tokens` and `output_tokens`)
- Sum across all traces for per-run totals

**Cost estimation** (from the cookbook's `estimate_cost` pattern):
Apply per-token pricing to recorded usage:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|----------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| gpt-5.4-mini | ~$0.15 | ~$0.60 |
| Claude Sonnet | ~$3.00 | ~$15.00 |

**Key metric from cookbook:** `cost_per_correct_pct` = total_cost / correctness_mean

State clearly when using estimates vs actual costs.

### Step 4: Compute Tradeoff Metrics

For each evaluation run, calculate:

| Metric | Formula |
|--------|---------|
| Pass Rate | (traces passing all scorers) / (total traces) |
| Avg Cost per Trace | total_cost / num_traces |
| Cost per Qualified Trace | total_cost / num_passing_traces |
| Quality/Cost Ratio | pass_rate / avg_cost_per_trace |
| Avg Latency | mean(trace_duration_ms) |
| Token Efficiency | pass_rate / avg_tokens_per_trace |

### Step 5: Rank and Recommend

Rank configurations by **Cost per Qualified Trace** (lower is better at same quality):
1. Best value: highest quality/cost ratio
2. Best quality: highest pass rate regardless of cost
3. Most economical: lowest cost that still meets threshold (>=80% pass rate)

### Step 6: Generate Report

## Output Format

```
# Cost-Quality Tradeoff Report
## Agent: [name] | Experiment: [id]
## Date: [timestamp] | Runs Compared: N

### Summary Matrix
| Run | Config/Model | Pass Rate | Avg Cost/Trace | Cost/Qualified Trace | Latency (p50) | Verdict |
|-----|-------------|-----------|----------------|---------------------|---------------|---------|
| [id] | [model/config] | XX% | $X.XXX | $X.XXX | Xms | BEST VALUE |
| [id] | [model/config] | XX% | $X.XXX | $X.XXX | Xms | BEST QUALITY |
| [id] | [model/config] | XX% | $X.XXX | $X.XXX | Xms | MOST ECONOMICAL |

### Cost Breakdown
| Run | Input Tokens (avg) | Output Tokens (avg) | Total Cost | Traces |
|-----|-------------------|--------------------:|------------|--------|
| [id] | N | N | $X.XX | N |

### Recommendation
**[Configuration recommendation with rationale]**

Example: "GPT-4o-mini achieves 85% pass rate at $0.003/trace vs GPT-4o at 92% for $0.041/trace.
For this agent, GPT-4o-mini offers 28x better cost efficiency with only 7% quality gap —
recommended unless the use case requires >90% accuracy."

### Quality vs Budget Scenarios
| Budget/month | Recommended Config | Expected Quality | Traces/month |
|-------------|-------------------|-----------------|--------------|
| $50 | [config] | XX% pass rate | ~N |
| $200 | [config] | XX% pass rate | ~N |
| $500 | [config] | XX% pass rate | ~N |

### Next Steps
- [ ] [If clear winner] Switch to recommended configuration
- [ ] [If marginal difference] Run larger sample for statistical confidence
- [ ] [If cost too high] Consider `eval-loop` to improve quality at current model tier
- [ ] [If quality insufficient at any cost] Review agent architecture
```

## When Cost Data is Unavailable

If traces lack `mlflow.llm.cost` or `mlflow.chat.tokenUsage`:
1. State clearly: "Cost data not found in traces"
2. Recommend enabling cost tracking via MLflow autolog
3. Fall back to **latency-quality tradeoff** (latency correlates with token usage)
4. Still produce the quality comparison portion of the report

## Anti-patterns

- Never fabricate cost data — state when estimates are used
- Never compare runs with vastly different trace counts without normalizing
- Never recommend based on cost alone — quality must meet minimum threshold
- Never ignore latency — a cheap but slow agent may not be suitable for real-time use
- Never `import mlflow` in the sandbox — all data retrieval via MCP
