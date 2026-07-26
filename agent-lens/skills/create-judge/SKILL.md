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

The [MLflow Custom Judges Cookbook](https://mlflow.org/cookbook/custom-llm-judges/) shows three
types of custom judges. Agent Lens maps them to MCP tools:

| Cookbook Pattern | MLflow SDK | Agent Lens MCP Tool | When to Use |
|----------------|-----------|---------------------|-------------|
| `Guidelines(name=..., guidelines=[...])` | Built-in | `mcp_mlflow_register_llm_judge_scorer` | Rule-based checks (policy, format, tone) |
| `@scorer` with code logic | Built-in | Not available via MCP | Deterministic checks (use Guidelines approximation) |
| Custom LLM judge calling OpenAI | Custom | `mcp_mlflow_register_llm_judge_scorer` | Complex domain-specific evaluation |

**Default to Guidelines-style** — it covers most use cases and maps directly to `register_llm_judge_scorer`.

### Step 3: Generate Instructions

Compose instructions following the exact patterns from the MLflow cookbook:

**Pattern 1: Guidelines-style (most common)**

From the cookbook, `Guidelines` checks are lists of rules. Via MCP, compose them as instructions:

```
name: conciseness
instructions: |
  Check whether {{ outputs }} follows these guidelines when responding to {{ inputs }}:
  - Response must be under 500 words
  - Response must avoid unnecessary filler phrases
  Return "yes" if all guidelines are met, "no" if any are violated.
  Include a rationale explaining which guideline was violated.
```

**Pattern 2: Section/structure validation**

From the cookbook `has_required_sections` pattern:

```
name: has_required_sections
instructions: |
  Check whether {{ outputs }} contains all required sections: Overview, Details, Disclaimer.
  Return "yes" if all sections are present, "no" if any are missing.
  In the rationale, list which sections are missing.
```

**Pattern 3: Domain-specific judgment**

From the cookbook `medical_tone_judge` pattern:

```
name: medical_tone
instructions: |
  Rate the medical information in {{ outputs }} responding to {{ inputs }}.
  Check:
  1. Uses appropriate medical terminology
  2. Avoids definitive diagnostic language
  3. Includes a disclaimer about consulting professionals
  4. Maintains a neutral, informative tone
  Return "yes" if all criteria are met, "no" if any fail.
```

**Pattern 4: Source citation check**

From the cookbook `source_citation` pattern:

```
name: source_citation
instructions: |
  Check whether {{ outputs }} properly cites sources when making factual claims.
  Guidelines:
  - Response must cite sources when making factual claims
  - Response must not present opinions as facts
  Return "yes" if citation practices are adequate, "no" otherwise.
```

### Step 4: Register the Scorer

Call `mcp_mlflow_register_llm_judge_scorer`:
- `name` — descriptive snake_case name (e.g., `privacy_policy_compliance`)
- `instructions` — the composed evaluation instructions
- `experiment_id` — target experiment from Step 1

### Step 5: Verify Registration

Call `mcp_mlflow_list_scorers` with `experiment_id` set to the target experiment to confirm the new scorer appears.

### Step 6: Dry-Run Validation

Run the new judge on 3-5 traces to validate it works:

1. `mcp_mlflow_search_traces` — get 3-5 recent trace IDs from the experiment
2. `mcp_mlflow_evaluate_traces` — run with the new scorer name and those trace IDs

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
