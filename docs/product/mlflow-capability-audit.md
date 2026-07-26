# MLflow End-to-End Capability Audit for Agent Lens

*Owner: Engineering*
*Last updated: July 2026*
*MLflow version audited: 3.8+ (OSS) and Databricks-managed MLflow*
*Status: Complete*

---

## Purpose

This document is the authoritative reference for M2 architecture decisions. It maps every planned Agent Lens feature against MLflow's capability surface, producing a **Build vs. Consume** decision for each. The goal: eliminate duplication, maximize upstream leverage, and build only what MLflow cannot provide.

---

## Area 1: Agent Registry — LoggedModel vs. Custom Registry

**Agent Lens planned:** Custom registry store in Gateway (F4, issue #41)

### What MLflow Provides

**LoggedModel** is a first-class entity in MLflow 3.0+, independent of runs:

| API | Purpose |
|---|---|
| `mlflow.create_external_model(name, model_type, tags, params)` | Register agents stored outside MLflow |
| `mlflow.search_logged_models(filter_string, order_by, max_results)` | Find models by metrics, params, attributes |
| `mlflow.set_logged_model_tags(model_id, tags)` | Store arbitrary key-value metadata |
| `mlflow.log_model_params(params, model_id)` | Store agent configuration parameters |
| `mlflow.get_logged_model(model_id)` | Retrieve full model details |
| `mlflow.finalize_logged_model(model_id, status)` | Set status to READY or FAILED |
| `mlflow.delete_logged_model_tag(model_id, key)` | Remove a tag |

**LoggedModel data model fields:** `model_id`, `name`, `model_type`, `tags` (dict), `params` (dict), `metrics` (list[Metric]), `creation_timestamp`, `status` (PENDING/READY/FAILED), `source_run_id`, `experiment_id`.

### MCP Tool Availability

The **official** MLflow MCP server (`mlflow mcp run`) organizes tools into categories controlled by `MLFLOW_MCP_TOOLS`:

| Category | Tools Included |
|---|---|
| `genai` (default) | `traces`, `scorers`, `experiments`, `runs` |
| `ml` | `experiments`, `runs`, `models`, `deployments` |
| `all` | All of the above |

**Critical finding:** The official MLflow MCP server (`mlflow mcp run`) documentation only lists trace-management tools (10 tools: `search_traces`, `get_trace`, `delete_traces`, `set_trace_tag`, `delete_trace_tag`, `log_feedback`, `log_expectation`, `get_assessment`, `update_assessment`, `delete_assessment`) plus scorer and experiment tools. The `models` category is documented as available when `MLFLOW_MCP_TOOLS=ml` or `MLFLOW_MCP_TOOLS=all`, but the exact LoggedModel tools exposed via official MCP require verification at deployment time.

**Action required:** Set `MLFLOW_MCP_TOOLS=all` on the MLflow MCP server and verify which LoggedModel tools are exposed. Add confirmed tools to the `config.yaml` allowlist. If the official MCP does not expose LoggedModel tools, Agent Lens can still use LoggedModel data via Gateway (Gateway calls MLflow Python SDK directly for registry operations).

Third-party MLflow MCPs (e.g., `us-all/mlflow-mcp-server` with 82 tools across 8 categories including `logged-models`) explicitly expose LoggedModel tools. If the official MCP surface is insufficient, consider using a community MCP or building a thin Gateway wrapper.

### search_logged_models Tag Filtering — Confirmed Documentation Bug

| Source | Statement |
|---|---|
| [Search Logged Models docs](https://mlflow.org/docs/latest/ml/search/search-models/) | **"No Tag Support: Unlike `search_runs`, the `search_logged_models` API does not support filtering by tags"** |
| [Tracking API docs](https://mlflow.org/docs/latest/ml/tracking/tracking-api/) | Shows example: `filter_string="tags.environment = 'production'"` |
| [GitHub issue #17920](https://github.com/mlflow/mlflow/issues/17920) | **Confirmed doc bug** — tag filtering IS supported. Fix in [PR #18364](https://github.com/mlflow/mlflow/pull/18364). |

**Assessment:** The "No Tag Support" statement is a **confirmed documentation bug**. Tag filtering IS supported in OSS `search_logged_models` using `tags.<key>` syntax. This is excellent news for Agent Lens — qualification status tags can be queried directly without client-side filtering.

**Pagination note:** `search_logged_models` is capped at **50 results per page** with `page_token` pagination. At M2 scale (< 100 agents), this means at most 2 pages to fetch the full fleet.

### Qualification Metadata Modeling

LoggedModel tags are `dict[str, str]` with no documented size limits. Agent Lens qualification metadata CAN be stored as tags:

| Tag Key | Example Value | Purpose |
|---|---|---|
| `agentlens.qualification_status` | `QUALIFIED` | Current qualification state |
| `agentlens.qualification_timestamp` | `2026-07-25T14:30:00Z` | When qualified |
| `agentlens.qualification_expiry` | `2026-10-25T14:30:00Z` | TTL-based expiry |
| `agentlens.qualifying_user` | `platform-team@example.com` | Who qualified |
| `agentlens.qualification_evidence_run_id` | `run_abc123` | Evaluation run with evidence |
| `agentlens.owner_team` | `data-science` | Owning team |
| `agentlens.framework` | `langchain` | Agent framework |
| `agentlens.namespace` | `production` | K8s namespace |

### Gap Analysis: What Agent Lens Adds

| Capability | MLflow Provides | Agent Lens Must Build |
|---|---|---|
| Agent inventory | LoggedModel with tags | Fleet aggregation view across experiments |
| Search by qualification status | Tag filtering confirmed working (doc bug fixed) | Direct `search_logged_models` with `tags.agentlens.qualification_status` |
| Qualification lifecycle | Tag storage only | QUALIFIED → PENDING → EXPIRED state machine with TTL computation |
| Auto-discovery from K8s | Nothing | K8s API integration (M3+) |
| Fleet health summary | Nothing | Aggregate trace health + qualification status |

### Decision: **Consume + Extend**

Use MLflow LoggedModel as the storage layer for agent metadata. Agent Lens Gateway adds the fleet aggregation, status computation, and lifecycle management on top. Do NOT build a separate agent inventory store — store everything in MLflow via `set_logged_model_tags`.

**Impact on implementation-plan-m2.md:**
- S5.T3 (MLflow experiment sync) → Change to "MLflow LoggedModel sync" using `search_logged_models`
- S5.T5 (`get_registry` MCP tool) → Returns data aggregated from MLflow LoggedModel + computed status
- Gateway `stores/registry.py` → Becomes a cache/view over MLflow LoggedModel data, not a primary store
- Add LoggedModel MCP tools to `config.yaml` allowlist

---

## Area 2: Evaluation and Scorers — Built-in vs. Custom Profiles

**Agent Lens planned:** Expanded scorer profiles (F6, issue #43)

### Complete Built-in LLM Judge Inventory

#### Response Quality Judges

| Judge | What It Evaluates | Ground Truth Required? | Trace Required? | OSS Available? |
|---|---|---|---|---|
| `RelevanceToQuery` | Response addresses user's input | No | No | **Yes** |
| `Correctness` | Expected facts supported by response | Yes (`expected_facts`) | No | **Yes** |
| `Completeness` | All questions in prompt addressed | No | No | **Yes** (experimental) |
| `Fluency` | Grammar and natural flow | No | No | **Yes** |
| `Safety` | No harmful or toxic content | No | No | **Databricks-only** (OSS "soon") |
| `Equivalence` | Response equivalent to expected output | Yes | No | **Yes** |
| `Summarization` | Faithful, comprehensive, concise summary | No | No | **Yes** |
| `Guidelines` | Adheres to provided guidelines | Yes (guidelines text) | No | **Yes** |
| `ExpectationsGuidelines` | Meets specific expectations + guidelines | Yes | No | **Yes** |

#### RAG Judges

| Judge | What It Evaluates | Ground Truth Required? | Trace Required? | OSS Available? |
|---|---|---|---|---|
| `RetrievalRelevance` | Retrieved docs relevant to request | No | **Yes** (RETRIEVER span) | **Databricks-only** (OSS "soon") |
| `RetrievalGroundedness` | Response grounded in retrieved info | No | **Yes** (RETRIEVER span) | **Yes** |
| `RetrievalSufficiency` | Retrieved docs have all needed info | Yes | **Yes** (RETRIEVER span) | **Yes** |

#### Tool Call Judges (Experimental)

| Judge | What It Evaluates | Ground Truth Required? | Trace Required? | OSS Available? |
|---|---|---|---|---|
| `ToolCallCorrectness` | Correct tool calls and arguments | No | **Yes** | **Yes** (experimental) |
| `ToolCallEfficiency` | No redundant or unnecessary calls | No | **Yes** | **Yes** (experimental) |

#### Multi-Turn Judges (Experimental, MLflow 3.7+)

| Judge | What It Evaluates | Requires Session? | OSS Available? |
|---|---|---|---|
| `ConversationCompleteness` | All user questions addressed | Yes | **Yes** (experimental) |
| `ConversationalGuidelines` | Responses comply with guidelines | Yes | **Yes** (experimental) |
| `ConversationalRoleAdherence` | Maintains assigned role | Yes | **Yes** (experimental) |
| `ConversationalSafety` | Safe and non-harmful responses | Yes | **Yes** (experimental) |
| `ConversationalToolCallEfficiency` | Efficient tool usage across conversation | Yes | **Yes** (experimental) |
| `KnowledgeRetention` | Retains info from earlier inputs | Yes | **Yes** (experimental) |
| `UserFrustration` | User frustration detected/resolved | Yes | **Yes** (experimental) |

**Total: 23 built-in judges** (9 response quality + 3 RAG + 2 tool call + 7 multi-turn + 2 Databricks-only)

#### `get_all_scorers()` Returns (OSS)

```python
[ExpectationsGuidelines(), Safety(), Correctness(), RelevanceToQuery(),
 RetrievalRelevance(), RetrievalSufficiency(), RetrievalGroundedness()]
```

Note: `Safety` and `RetrievalRelevance` are returned by `get_all_scorers()` but are Databricks-only at runtime. Calls will fail on OSS MLflow.

**Important note on Safety:** `ConversationalSafety` (multi-turn) IS available in OSS despite `Safety` (single-turn) being Databricks-only. This means OSS deployments can still assess safety in multi-turn conversations.

### Guardrails AI Integration

MLflow 3.10+ integrates Guardrails AI validators:

| Scorer | Detection Method | What It Detects |
|---|---|---|
| `ToxicLanguage` | NLP classification model | Toxic, offensive, harmful content |
| `NSFWText` | Content classification model | Adult/explicit content |
| `DetectJailbreak` | BERT-based classifier | Prompt injection/jailbreak attempts |
| `DetectPII` | Microsoft Presidio NER | Emails, phone numbers, names, locations |
| `SecretsPresent` | Regex pattern matching | API keys, tokens, passwords |
| `GibberishText` | Perplexity-based coherence scoring | Incoherent/nonsensical text |

**MCP availability: Python SDK only, NOT via MCP `evaluate_traces`.** Guardrails scorers require local model downloads (BERT, Presidio), the `guardrails-ai` package plus hub installs, and validator-specific kwargs. They are not resolvable by name in `evaluate_traces` unless manually registered. For Agent Lens, these would need a thin Python wrapper that runs locally and logs results via `log_feedback`.

### Custom Scorers and MCP

- **`@scorer` decorator:** Creates code-based scorers (Python functions). These ARE accessible via MCP `evaluate_traces` after registration via `scorer.register(name="my_scorer")`.
- **Resolution order:** The `resolve_scorers()` function in `evaluate_traces` first checks built-in scorers via `get_all_scorers()` (class name match), then falls back to `get_scorer(name)` for registered custom scorers.
- **`list_scorers` MCP tool:** Returns all **registered** scorers for the experiment. Does NOT automatically include all built-in scorers (those are resolved by class name directly). Works on both OSS and Databricks.
- **`evaluate_traces` MCP tool:** Accepts scorer names as strings. Built-in scorers are resolved by class name (e.g., `"Correctness"`). Custom scorers are resolved by registered name. Both paths work via MCP.
- **OSS caveat:** Registration of custom scorers that execute arbitrary code requires `MLFLOW_ALLOW_CUSTOM_SCORER_CODE_EXECUTION=true` on the tracking server.

### Agent Lens Scorer Profiles: Config, Not Code

Given the scorer surface, Agent Lens profiles should be **named groupings that map to specific scorer names passed to `evaluate_traces`**. No custom scorer infrastructure is needed.

| Profile | Scorers | Notes |
|---|---|---|
| **RAG** | `RelevanceToQuery`, `RetrievalGroundedness` | Existing. Add `RetrievalSufficiency` if ground truth exists. |
| **Tool-Calling** | `ToolCallCorrectness`, `ToolCallEfficiency`, `RelevanceToQuery` | Existing. All experimental. |
| **Chat** | `RelevanceToQuery`, `Guidelines` | Existing. |
| **Safety** (NEW) | `Safety`, `Guidelines` | Safety is Databricks-only. Fallback: `Guidelines` with safety criteria on OSS. |
| **Comprehensive** (NEW) | All available non-experimental scorers | Call `list_scorers` to enumerate; exclude RAG scorers if no RETRIEVER spans. |
| **Multi-Turn** (NEW, M3) | `ConversationCompleteness`, `ConversationalSafety`, `UserFrustration` | Requires session ID on traces. |
| **Custom** | User-specified scorer names | Validate against `list_scorers` before evaluation. |

### Decision: **Consume (with config layer)**

Use MLflow's built-in scorers exclusively. Agent Lens adds a thin configuration layer that maps profile names to scorer lists. No custom scorer code. The `evaluate-agent` skill simply passes the resolved scorer list to `mcp_mlflow_evaluate_traces`.

**OSS limitation:** `Safety` and `RetrievalRelevance` are Databricks-only. For OSS deployments, the Safety profile must fall back to `Guidelines` with explicit safety criteria text. Document this limitation clearly.

**Impact on implementation-plan-m2.md:**
- S6.T2 (Safety + Comprehensive profiles) → Profiles are YAML config files, not scorer code
- S6.T3 (Custom profile configuration) → Simpler than planned; just a mapping of profile name → scorer list + threshold overrides
- S2.T2 (Scorer profile resolution) → Unchanged; resolves profile → scorer names, validates with `list_scorers`

---

## Area 3: Version Comparison — MLflow UI vs. Custom Skill

**Agent Lens planned:** Evaluation Comparison skill (F7, issue #44)

### What MLflow Provides

| Capability | Mechanism | Access |
|---|---|---|
| Side-by-side run comparison | MLflow UI: select 2 runs → Compare | UI only |
| Per-scorer aggregate metrics | Displayed in comparison view | UI only |
| Per-example trace diffs | Available in comparison view | UI only |
| Programmatic metrics access | `describe_run` MCP tool returns run metrics including evaluation scorer results | MCP |
| Run listing | `list_runs` MCP tool (**no filter support** — returns all runs, filter client-side) | MCP |
| Run search (proposed) | `search_runs` proposed in [issue #23034](https://github.com/mlflow/mlflow/issues/23034), PR [#23049](https://github.com/mlflow/mlflow/pull/23049) pending | Not yet available |
| Trace filtering by model | `search_traces(model_id=...)` — confirmed working for version-to-version trace comparison | MCP |

### `describe_run` MCP Tool

Returns run metadata including:
- Run name, status, start/end time
- Parameters (all logged params)
- Metrics (all logged metrics, including evaluation scorer results)
- Tags

Evaluation metrics from `evaluate_traces` are logged as run metrics, so `describe_run` on an evaluation run returns pass rates and scorer results.

### Value Assessment

| Factor | MLflow UI | Chat Skill |
|---|---|---|
| Requires browser access | Yes | No |
| Works in CI/CD context | No | Yes (via Gateway) |
| Natural language query | No | Yes ("compare latest eval to last week") |
| Accessible from Hermes chat | No | Yes |
| Data already available via MCP | — | Yes (`describe_run`, `list_runs`) |

**Assessment:** The comparison skill adds genuine value because Agent Lens users interact via chat, not the MLflow UI. The skill is a **chat interface to data MLflow already has** — it calls `describe_run` on two run IDs and computes deltas. No new data storage is needed.

### Decision: **Consume + Chat Interface**

The `compare-evaluations` skill calls existing MCP tools (`describe_run`, `list_runs`) and formats the comparison in chat. Zero new infrastructure. The skill is essentially a prompt template that structures MCP calls and presents results.

**Impact on implementation-plan-m2.md:**
- S6.T4 → Simplified. Skill calls `describe_run` on two runs, computes per-scorer delta, flags threshold crossings. No Gateway dependency.
- Remove dependency on Gateway MCP for this skill.

---

## Area 4: Production Monitoring and Alerting

**Agent Lens planned:** Alerting (F14, issue #50), Trend Analysis (F15, issue #51), Cost Tracking (F12, issue #49)

### Automatic Online Evaluation

MLflow's `ScorerScheduleConfig` enables scheduled scorers on production traces:

```python
from mlflow.genai.scheduled_scorers import ScorerScheduleConfig
from mlflow.genai.scorers import Safety

config = ScorerScheduleConfig(
    scorer=Safety(),
    scheduled_scorer_name="production_safety",
    sample_rate=0.2,
    filter_string="trace.status = 'OK'",
)
```

**Critical limitation: Databricks-only.** Scheduled scorers are "part of Databricks Lakehouse Monitoring for GenAI." They are NOT available in OSS MLflow. Agent Lens on OpenShift cannot use this feature.

For OSS, Agent Lens must implement its own periodic evaluation (the existing `evaluate-agent` skill run on a schedule via CronJob or Hermes `cronjob` toolset).

### Token Usage and Cost Tracking

MLflow captures token usage and cost per trace span:

| Attribute | Location | Fields |
|---|---|---|
| Token usage | `mlflow.chat.tokenUsage` on spans | `input_tokens`, `output_tokens`, `total_tokens` |
| Cost | `mlflow.llm.cost` on spans | `input_cost`, `output_cost`, `total_cost` (USD) |
| Trace-level aggregation | `trace.info.token_usage` | Rolled up from all spans |

**Known bug:** [mlflow/mlflow#24059](https://github.com/mlflow/mlflow/issues/24059) — OpenAI autolog stores token usage under `"usage"` instead of `"mlflow.chat.tokenUsage"`, causing trace-level aggregation to report 0 tokens for some spans. This affects Agent Lens if target agents use OpenAI autolog with streaming.

**Cost computation from traces:** Yes, cost CAN be computed from trace data alone if `mlflow.llm.cost` is populated. For models without automatic cost tracking, manual `set_attribute` is required on spans.

**MCP access:** `search_traces` with `extract_fields="info.token_usage"` can retrieve token data. However, aggregation (sum across traces, per-agent totals) must be done client-side.

### search_traces Performance

- **Pagination:** `max_results` parameter controls page size. Default is **100**, hard cap is **500** per request (enforced server-side via protobuf). Client-side pagination via `page_token`.
- **Aggregation:** `search_traces` returns raw trace data. No server-side aggregation exists. Computing error rates, latency percentiles, and token sums requires fetching all matching traces and aggregating in Python/code-execution.
- **Scale concern:** For 100+ traces, this means multiple paginated API calls and client-side computation. At 500 traces/page, a 1000-trace aggregation requires 2 API calls. Acceptable at M2 scale but may need optimization at M3+ scale.
- **Databricks enhancement:** On Databricks, `MLFLOW_TRACING_SQL_WAREHOUSE_ID` can be set for better performance on large datasets.

### Filter capabilities in OSS search_traces

| Field | Operators | Example |
|---|---|---|
| `trace.status` | `=`, `!=` | `trace.status = "OK"` |
| `trace.timestamp_ms` | `=`, `!=`, `>`, `<`, `>=`, `<=` | Time range filtering |
| `trace.execution_time_ms` | `=`, `!=`, `>`, `<`, `>=`, `<=` | Latency filtering |
| `trace.name` | `=`, `!=`, `LIKE`, `ILIKE`, `RLIKE` | Agent name matching |
| `tag.<key>` | `=`, `!=` (OSS: only `=` and `!=`) | `tag.environment = "production"` |
| `span.name`, `span.type` | `=`, `!=`, `LIKE`, `ILIKE`, `RLIKE` | Span-level filtering |
| `metadata.<key>` | `=`, `!=` (OSS: only `=` and `!=`) | `metadata.mlflow.trace.user = "user_123"` |

**Note:** `trace.token_count`, `span.attributes.*`, `feedback.*` filters are **Databricks / Unity Catalog only**.

### Alerting Status

No built-in alerting exists in OSS MLflow. Feature request [mlflow/mlflow#23958](https://github.com/mlflow/mlflow/issues/23958) is open but not implemented. Agent Lens must build its own alerting mechanism.

### Decision: **Build on MLflow Data**

MLflow provides the raw data (traces, token usage, scorer results) but no aggregation, trending, or alerting. Agent Lens builds all monitoring features on top of MLflow's data layer:

| Capability | MLflow Provides | Agent Lens Builds |
|---|---|---|
| Token usage per trace | `mlflow.chat.tokenUsage` span attribute | Per-agent cost aggregation |
| Trace health data | `search_traces` with status/latency filters | Error rate, latency percentile computation |
| Evaluation scores | `evaluate_traces` results as run metrics | Trend analysis over time |
| Alerting | Nothing | Threshold-based alerts (M3) |
| Automatic evaluation | Databricks-only `ScorerScheduleConfig` | CronJob-based `evaluate-agent` (M3) |

**Impact on implementation-plan-m2.md:**
- S6.T1 (aggregate-traces skill) → Calls `search_traces` with time-range filter, aggregates client-side. No change needed.
- M3 alerting/monitoring → Must be built entirely by Agent Lens. No MLflow shortcut.
- Cost tracking → Can use `search_traces` + `extract_fields` for token data. No Prometheus needed for basic cost views.

---

## Area 5: Prompt Registry — Skills Management

**Agent Lens planned:** Skills as SKILL.md files managed via ConfigMaps

### What MLflow Prompt Registry Provides

| Feature | Details |
|---|---|
| Versioned prompts | Immutable versions with commit messages, diff views |
| Template variables | `{{variable}}` syntax with Jinja2 support |
| Tags and search | `search_prompts(filter_string="task='summarization'")` with pagination |
| Aliases | `production`, `staging`, `@latest` for environment management |
| Model config | Optional model name, temperature, max_tokens per prompt |
| Response format | Optional Pydantic model or JSON schema for structured output |
| Immutability | Once created, a version's template cannot be modified |
| MCP tools | The official MLflow MCP server does **NOT** expose Prompt Registry tools — only trace/assessment tools are documented. Would need custom MCP wrapper around `mlflow.genai.register_prompt()` / `search_prompts()`. |

### Could Agent Lens Skills Be Stored as Prompts?

**No, not for M2.** Key mismatches:

| Dimension | SKILL.md Files | MLflow Prompts |
|---|---|---|
| Content type | Markdown instruction documents (200-500 lines) | Template strings with variables |
| Purpose | Multi-step procedural instructions for LLM | Parameterized input templates for LLM calls |
| Variables | None (skills are complete instructions) | `{{variable}}` substitution |
| Size | 200-500 lines per skill (~5-20 KB) | 100K+ chars supported (5K limit removed in [PR #16377](https://github.com/mlflow/mlflow/pull/16377)). Skills fit technically but are a semantic mismatch. |
| Deployment | ConfigMap → volume mount → file system | API-based, environment-decoupled |
| Versioning | Git-based (ConfigMap from repo) | Built-in version tracking with diffs |
| Runtime access | File system read by Hermes skill curator | API call to `load_prompt()` |

Skills are fundamentally different from prompts. SKILL.md files are instruction manuals for the LLM, not parameterized templates. The Prompt Registry is designed for input templates like "Summarize the following: {{text}}" — not 500-line procedural documents.

### Trade-offs: ConfigMap vs. Prompt Registry

| Factor | ConfigMap (Current) | Prompt Registry (Alternative) |
|---|---|---|
| Version control | Git (deploy-time) | Built-in (runtime) |
| K8s native | Yes | No (external dependency) |
| Hot reload | Requires pod restart or ConfigMap watcher | API-based, could hot-reload |
| Environment management | Kustomize overlays | Aliases (production/staging) |
| Team collaboration | Git PRs | MLflow UI |
| Offline access | Always available (local filesystem) | Requires MLflow server |

### Decision: **Keep ConfigMaps for M2; Evaluate for M4+**

Skills stay as ConfigMap-mounted SKILL.md files for M2. The Prompt Registry is architecturally mismatched for skill-length instruction documents. However, for M4+ consideration: shorter, parameterized elements (scorer profile configs, threshold definitions, custom guideline templates) could potentially use the Prompt Registry.

**Impact on implementation-plan-m2.md:** No changes. ConfigMap approach is confirmed as correct for M2.

---

## Area 6: Webhooks and CI/CD

**Agent Lens planned:** CI/CD Quality Gate API (F1, issue #18)

### Complete Webhook Event Inventory

| Event | Entity | Action | Payload |
|---|---|---|---|
| `registered_model.created` | Registered Model | Created | name, tags, description |
| `model_version.created` | Model Version | Created | name, version, source, tags |
| `model_version_tag.set` | Model Version Tag | Set | name, version, key, value |
| `model_version_tag.deleted` | Model Version Tag | Deleted | name, version, key |
| `model_version_alias.created` | Model Version Alias | Created | name, version, alias |
| `model_version_alias.deleted` | Model Version Alias | Deleted | name, alias |
| `prompt.created` | Prompt | Created | name, tags |
| `prompt_version.created` | Prompt Version | Created | name, version, template |
| `prompt_tag.set` | Prompt Tag | Set | name, key, value |
| `prompt_tag.deleted` | Prompt Tag | Deleted | name, key |
| `prompt_version_tag.set` | Prompt Version Tag | Set | name, version, key, value |
| `prompt_version_tag.deleted` | Prompt Version Tag | Deleted | name, version, key |
| `prompt_alias.created` | Prompt Alias | Created | name, version, alias |
| `prompt_alias.deleted` | Prompt Alias | Deleted | name, alias |
| `budget_policy.exceeded` | Budget Policy | Exceeded | policy details |

**15 event types total.**

### What Webhooks Do NOT Support

| Missing Event | Impact on Agent Lens |
|---|---|
| `trace.logged` | Cannot trigger on new production traces |
| `evaluation.completed` | Cannot trigger on evaluation results |
| `assessment.logged` | Cannot trigger on feedback/expectations |
| `scorer.result` | Cannot trigger on individual scorer outcomes |
| `logged_model.created` | Cannot trigger when new agents are registered |

### CI/CD Gate: Webhooks Cannot Replace Gateway

| Requirement | Webhooks | Gateway API |
|---|---|---|
| Synchronous pass/fail | **No** — async notification only | **Yes** — POST returns verdict |
| Request-response | **No** — fire and forget | **Yes** — caller blocks for result |
| Custom threshold logic | **No** — no evaluation context | **Yes** — configurable thresholds |
| CI/CD exit code | **No** — no caller waiting | **Yes** — 200=PASS, 400/422=FAIL |

**Confirmed: The CI/CD quality gate requires Agent Lens Gateway. MLflow webhooks are insufficient.**

### Webhook-Triggered Evaluation (Enhancement Opportunity)

While webhooks cannot provide synchronous pass/fail, they CAN trigger asynchronous evaluation:

```
model_version.created webhook → POST to Gateway → Gateway runs evaluate_traces → stores result in audit trail
```

This is an M3+ enhancement: when a new model version is registered in MLflow, a webhook could trigger Agent Lens to automatically evaluate it. The result would be recorded in the audit trail, and the agent's qualification status would be updated.

**Not needed for M2** but architecturally sound for future automation.

### budget_policy.exceeded Webhook

This webhook is part of **AI Gateway**, not the tracing system. It fires when cumulative LLM spend routed through the gateway exceeds a configured USD threshold within a time window (daily/weekly/monthly). Payload includes `budget_policy_id`, `budget_amount`, `current_spend`, `duration_unit`, `window_start`.

**Limitation:** Only covers LLM spend routed through AI Gateway. Cannot alert on trace-level cost aggregations, scorer costs, or LLM calls that bypass the gateway. For comprehensive cost alerting, Agent Lens must implement its own aggregation from trace token data.

### Decision: **Build (Gateway is Required)**

The CI/CD quality gate is a net-new build. MLflow webhooks are event-driven notifications, not synchronous verdicts. The Gateway REST API (`POST /api/v1/gate/evaluate`) is essential and cannot be replaced by MLflow.

**Potential enhancement (M3+):** Use `model_version.created` webhook to trigger automatic evaluation.

**Impact on implementation-plan-m2.md:** No changes. Gateway design is confirmed as necessary.

---

## Area 7: Audit Trail

**Agent Lens planned:** Append-only checksummed audit trail (F3, issue #19)

### What MLflow Stores (Resembling Audit)

| MLflow Feature | What It Records | Limitations |
|---|---|---|
| Trace assessments (feedback) | Scorer results: name, value, rationale, source_type | Per-trace; no cross-trace queryability for decisions |
| Trace assessments (expectations) | Ground truth labels | Same as above |
| LoggedModel tags | Qualification metadata (if stored as tags) | Mutable; no history; no tamper evidence |
| Run history | Which evaluation runs were executed, when, with what scorers | No decision context; no actor identity |
| Trace tags | Arbitrary key-value metadata on traces | Mutable; no append-only guarantee |

### What Is Definitively Missing

| Requirement | MLflow Status | Agent Lens Must Build |
|---|---|---|
| Structured decision log | **Not provided** | JSON records: who, what, when, verdict, evidence |
| SHA-256 checksumming | **Not provided** | Each record checksummed with hash of previous record |
| Append-only guarantee | **Not provided** | Immutable JSONL file; no update/delete operations |
| Tamper evidence | **Not provided** | Hash chain; any modification breaks the chain |
| Actor identity | **Partially** — trace tags can store user, but not systematically | Mandatory `actor` field on every audit record |
| Compliance export | **Not provided** — `search_traces` exports to pandas DataFrame but not structured compliance formats | JSON Lines and CSV export for GRC teams |
| Cross-entity query | **Not provided** — assessments are per-trace | Query by experiment, date range, actor, event type |
| Decision context | **Not provided** | Why was agent qualified? What evidence? What thresholds? |

### Example Audit Record (Agent Lens)

```json
{
  "event_id": "evt_abc123",
  "event_type": "qualification",
  "timestamp": "2026-07-25T14:30:00Z",
  "actor": "platform-team@example.com",
  "experiment_id": "12345",
  "agent_name": "outreach-agent",
  "verdict": "QUALIFIED",
  "evidence": {
    "evaluation_run_id": "run_xyz789",
    "traces_evaluated": 200,
    "scorer_results": {
      "RelevanceToQuery": {"pass_rate": 0.92, "threshold": 0.80, "result": "PASS"},
      "RetrievalGroundedness": {"pass_rate": 0.85, "threshold": 0.80, "result": "PASS"}
    },
    "error_rate": 0.02
  },
  "checksum": "sha256:a1b2c3...",
  "previous_checksum": "sha256:d4e5f6..."
}
```

MLflow stores the scorer results (as assessments on traces) and the run metrics, but NOT the decision record that ties them together with actor identity, timestamps, and checksums.

**Upstream RFC:** [GitHub issue #22383](https://github.com/mlflow/mlflow/issues/22383) proposes a `trace_processors` callback for external signing of traces, but it is not yet implemented. Even if implemented, it would provide trace-level signing, not the structured decision log Agent Lens needs.

### Decision: **Build (Net-New)**

The audit trail is confirmed as a net-new build. MLflow stores evidence (assessments, tags, runs) but not decisions. Agent Lens needs to record "who qualified what, when, with what evidence, and was it tampered with" — MLflow does not do this. Traces themselves are mutable (no tamper-evidence), assessments lack verified actor identity (`source_id` is self-reported), and there is no append-only guarantee.

**MLflow as evidence source:** The audit trail REFERENCES MLflow data (run IDs, trace IDs, assessment IDs) but the trail itself is stored and managed by Agent Lens Gateway.

**Impact on implementation-plan-m2.md:** No changes. Audit trail design is confirmed as necessary.

---

## Build vs. Consume Decision Matrix

| Feature | MLflow Provides | Agent Lens Adds | Decision | M2 Impact |
|---|---|---|---|---|
| **Agent inventory** | LoggedModel + tags + search (tag filtering confirmed working — doc bug fixed) | Fleet aggregation, qualification lifecycle, status computation | **Consume + Extend** | Use LoggedModel as storage; Gateway adds lifecycle logic |
| **Evaluation scorers** | 23 built-in judges + `evaluate_traces` MCP | Profile groupings (YAML config), threshold config, OSS Safety fallback | **Consume + Config** | Profiles are config, not code; validate with `list_scorers` |
| **Version comparison** | UI comparison + `describe_run` MCP + `list_runs` MCP | Chat-based diff skill | **Consume + Chat Interface** | Skill calls existing MCP tools; no new infrastructure |
| **CI/CD quality gate** | Nothing (webhooks are async, not request-response) | Synchronous pass/fail REST API with threshold logic | **Build** | Gateway is essential and cannot be replaced |
| **Audit trail** | Assessment storage on traces (evidence) | Checksummed decision log with actor, export, query | **Build** | Net-new; references MLflow evidence but stores decisions independently |
| **SSO/OIDC** | Nothing | OAuth Proxy sidecar integration | **Build** | No change; SSO is infrastructure config |
| **Alerting** | Nothing in OSS (Databricks has scheduled scorers) | Threshold-based quality alerts | **Build (M3)** | Scheduled evaluation via CronJob, not MLflow schedulers |
| **Cost tracking** | Token usage + cost in trace spans | Per-agent aggregation, trending | **Build on MLflow data** | Fetch via `search_traces` + `extract_fields`; aggregate client-side |
| **Trend analysis** | Raw trace data with timestamps | Time-series aggregation, regression detection | **Build on MLflow data** | Same pattern as cost tracking |
| **Prompt/skill management** | Prompt Registry (templates, not instructions) | ConfigMap-based SKILL.md files | **Keep current** | Prompt Registry is architecturally mismatched for skills |
| **Webhook-triggered eval** | `model_version.created` webhook | Webhook → Gateway → auto-evaluate | **Evaluate for M3+** | Not needed for M2; architecturally viable |

---

## Key Findings and Recommendations

### 1. Expand MCP Tool Surface

Agent Lens currently uses 11 tools from the `genai` MCP category. To leverage LoggedModel for the agent registry, change `MLFLOW_MCP_TOOLS` to `all` (or `genai,models`) and add these tools to the allowlist:

```yaml
# config.yaml additions
mcp_servers:
  mlflow:
    tools:
      include:
        # ... existing 11 tools ...
        - search_logged_models
        - get_logged_model
        - set_logged_model_tags
        - create_logged_model
        - create_external_model
```

### 2. Gateway Scope Confirmed but Narrowed

The Gateway is still essential for:
- CI/CD quality gate (synchronous pass/fail)
- Audit trail (checksummed decision log)
- MCP server for Hermes (audit + registry tools)

The Gateway does NOT need to be a primary data store for agents. LoggedModel in MLflow is the source of truth for agent metadata. The Gateway's registry component becomes a **view** over MLflow data with computed status fields.

### 3. Safety Profile OSS Limitation

`Safety` and `RetrievalRelevance` judges are Databricks-only. For OSS deployments:
- Safety profile → Use `Guidelines` with explicit safety criteria: "Does the response avoid harmful, toxic, or biased content?"
- RAG profile → `RetrievalRelevance` unavailable; use `RetrievalGroundedness` + `RetrievalSufficiency` instead

Document this in the `evaluate-agent` skill and the operator guide.

### 4. Cost Tracking Is Feasible Without Prometheus

Token usage data in `mlflow.chat.tokenUsage` and cost data in `mlflow.llm.cost` span attributes provide everything needed for basic cost tracking. The `aggregate-traces` skill can fetch traces with `extract_fields="info.token_usage"` and compute totals client-side. No Prometheus integration needed for M2.

**Caveat:** [mlflow/mlflow#24059](https://github.com/mlflow/mlflow/issues/24059) — OpenAI autolog with streaming may report 0 tokens. Document as a known limitation.

### 5. Automatic Evaluation Is Not Available on OSS

MLflow's `ScorerScheduleConfig` (automatic online evaluation) is Databricks-only. For M3 monitoring, Agent Lens must implement its own scheduling:
- Option A: Hermes `cronjob` toolset (if enabled) running `evaluate-agent` periodically
- Option B: K8s CronJob calling the Gateway gate API
- Option C: Tekton scheduled pipeline

### 6. Multi-Turn Judges Are Available for analyze-session Skill

MLflow 3.7+ provides 7 multi-turn judges including `ConversationCompleteness`, `ConversationalSafety`, and `UserFrustration`. These are ideal for the existing `analyze-session` skill and can be incorporated into a future "Multi-Turn" scorer profile.

---

## Appendix: MCP Tool Inventory (Current vs. Expanded)

### Current Agent Lens MCP Tools (11)

| Tool | Category | Used By |
|---|---|---|
| `search_experiments` | experiments | evaluate-agent, quality-dashboard |
| `get_experiment` | experiments | evaluate-agent |
| `search_traces` | traces | trace-explorer, review-trace, quality-dashboard |
| `get_trace` | traces | review-trace, analyze-session |
| `log_trace_feedback` | traces | review-trace |
| `log_trace_expectation` | traces | review-trace, create-regression |
| `set_trace_tag` | traces | create-regression |
| `evaluate_traces` | scorers | evaluate-agent |
| `list_runs` | runs | quality-dashboard |
| `describe_run` | runs | quality-dashboard |
| `list_scorers` | scorers | evaluate-agent |

### Recommended Additions for M2 (5 new tools)

| Tool | Category | Used By (Planned) |
|---|---|---|
| `search_logged_models` | models | agent-registry skill, quality-dashboard |
| `get_logged_model` | models | agent-registry skill |
| `set_logged_model_tags` | models | evaluate-agent (store qualification) |
| `create_logged_model` | models | agent-registry skill (manual registration) |
| `create_external_model` | models | agent-registry skill (external agents) |

**Total after expansion: 16 official MLflow MCP tools**

Plus 4 Agent Lens Gateway MCP tools:
- `log_audit_event`
- `query_audit_trail`
- `get_registry` (aggregated view over LoggedModel data)
- `register_agent` (creates LoggedModel + tags)
