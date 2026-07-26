---
name: "create-judge"
description: "Create a custom LLM judge scorer from natural language criteria. Use when asked to build an evaluator, create a scorer, define quality criteria, or make a custom judge for domain-specific evaluation."
---

# Create Judge

Build domain-specific LLM judges conversationally via **upstream official MLflow MCP**.
Inspired by [MLflow Cookbook: Building Custom LLM Judges](https://mlflow.org/cookbook/building-custom-llm-judges).

MLflow's `make_judge` / `register_llm_judge_scorer` lets you define evaluation criteria declaratively.
Agent Lens translates your natural language quality requirements into a registered scorer.

## When to Use

- "Create a scorer that checks if my agent mentions the privacy policy"
- "I need a judge that validates tool calls follow our rate-limiting rules"
- "Build an evaluator for tone — professional but not robotic"
- "Make a custom judge for compliance checking"
- "Register a scorer that detects hallucinations about pricing"

## Strategy

### Step 1: Interview for Criteria

Ask the user:
1. **What** should the judge evaluate? (tone, accuracy, policy compliance, tool use, safety)
2. **How** should it decide pass/fail? (what makes a "pass" vs "fail")
3. **Which experiment** should it be registered under?

If the user is vague, propose concrete criteria and ask for confirmation.

### Step 2: Select Judge Type

| Type | When to Use | Template Variables |
|------|-------------|-------------------|
| Input/Output judge | Evaluate final answers | `{{ inputs }}`, `{{ outputs }}` |
| Expectation judge | Compare against ground truth | `{{ inputs }}`, `{{ outputs }}`, `{{ expectations }}` |
| Trace-based judge | Evaluate reasoning/tool use | `{{ inputs }}`, `{{ outputs }}`, `{{ trace }}` |

Default to **Input/Output** unless the user's criteria require trace inspection or expected outputs.

### Step 3: Generate Instructions

Compose the `instructions` parameter following MLflow best practices:

1. Be specific about what to evaluate
2. Describe what constitutes a pass vs fail
3. Reference the template variables
4. Keep instructions under 500 words

**Example (policy compliance):**
```
Evaluate whether the agent's response ({{ outputs }}) correctly references
the company's privacy policy when the user's question ({{ inputs }}) involves
personal data handling, data deletion, or data sharing.

PASS: The response explicitly mentions relevant privacy policy sections or
directs the user to the privacy policy page.
FAIL: The response discusses personal data without referencing the privacy
policy, or gives advice that contradicts the policy.
```

**Example (tool call validation):**
```
Analyze the agent's execution trace ({{ trace }}) to determine if tool calls
follow rate-limiting rules.

PASS: No more than 3 API calls per tool within a single trace, and retry
logic uses exponential backoff.
FAIL: More than 3 calls to the same tool without backoff, or any tool
called more than 5 times total.
```

### Step 4: Register the Scorer

Call `mcp_mlflow_register_llm_judge_scorer`:
- `name` — descriptive snake_case name (e.g., `privacy_policy_compliance`)
- `instructions` — the composed evaluation instructions
- `experiment_id` — target experiment from Step 1

### Step 5: Verify Registration

Call `mcp_mlflow_list_scorers` to confirm the new scorer appears in the list.

### Step 6: Dry-Run Validation

Run the new judge on 3-5 traces to validate it works:

1. `mcp_mlflow_search_traces` — get recent traces from the experiment
2. `mcp_mlflow_evaluate_traces` — run with the new scorer name, `max_traces` 3-5

Review results:
- If all pass or all fail, the judge may be too lenient/strict — offer to refine
- If scorer errors, check instructions for invalid template variables
- If mixed results, confirm with user that the judgments look correct

### Step 7: Report and Next Steps

## Output Format

```
## Custom Judge Created

| Field | Value |
|-------|-------|
| Name | [scorer_name] |
| Type | Input/Output / Expectation / Trace-based |
| Experiment | [experiment_name] (ID: [id]) |
| Registered | [timestamp] |

### Instructions Summary
[1-2 sentence summary of what the judge evaluates]

### Validation Results (dry-run on N traces)
| Trace | Verdict | Rationale (summary) |
|-------|---------|---------------------|
| [id]  | PASS/FAIL | [brief reason] |
| ...   | ...     | ...                 |

### Next Steps
- Use in `evaluate-agent` by specifying scorer: [scorer_name]
- Combine with built-in scorers for comprehensive evaluation
- Refine instructions if validation results don't match expectations
```

## Naming Conventions

| Domain | Suggested Name Pattern |
|--------|----------------------|
| Policy compliance | `{policy_name}_compliance` |
| Tone/style | `tone_{descriptor}` |
| Safety | `safety_{attack_type}` |
| Tool usage | `tool_{validation_type}` |
| Domain accuracy | `{domain}_accuracy` |

## Anti-patterns

- Never create judges with vague instructions ("evaluate quality")
- Never skip the dry-run validation step
- Never register a judge without confirming the experiment_id
- Never use template variables the judge type doesn't support
- Never `import mlflow` in the sandbox — all registration via MCP
