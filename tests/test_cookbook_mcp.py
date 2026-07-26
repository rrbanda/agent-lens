#!/usr/bin/env python3
"""Test cookbook features against real MLflow MCP."""
import subprocess, json, os, time, select

token = open('/var/run/secrets/kubernetes.io/serviceaccount/token').read().strip()
env = dict(os.environ)
env['MLFLOW_TRACKING_TOKEN'] = token
env['NO_COLOR'] = '1'

proc = subprocess.Popen(['mlflow','mcp','run'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

def send(msg):
    proc.stdin.write(json.dumps(msg) + '\n')
    proc.stdin.flush()

def read_response(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        ready, _, _ = select.select([proc.stdout], [], [], 0.5)
        if ready:
            line = proc.stdout.readline()
            if line:
                try:
                    return json.loads(line.strip())
                except:
                    pass
    return None

def call_tool(name, args=None):
    call_tool.counter += 1
    send({'jsonrpc':'2.0','id':call_tool.counter,'method':'tools/call','params':{'name':name,'arguments':args or {}}})
    r = read_response(timeout=20)
    if r and 'result' in r:
        c = r['result'].get('content', [])
        txt = c[0]['text'] if c else ''
        return ('PASS', txt)
    elif r and 'error' in r:
        return ('FAIL', json.dumps(r['error'])[:300])
    return ('NO_RESP', str(r))
call_tool.counter = 10

# Initialize
send({'jsonrpc':'2.0','id':0,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'t','version':'1'}}})
r = read_response()
send({'jsonrpc':'2.0','method':'notifications/initialized'})
time.sleep(0.5)
print("MCP initialized\n")

results = {}

# =====================================================
# TEST 1: list_scorers --builtin (create-judge, evaluate-agent)
# =====================================================
print("=" * 60)
print("TEST 1: list_scorers --builtin")
print("Cookbook: Building Custom LLM Judges, EDD, Red-Teaming")
s, t = call_tool('list_scorers', {'builtin': 'true'})
print(f"  Result: {s}")
if s == 'PASS':
    print(f"  Scorers:\n{t[:600]}")
else:
    print(f"  {t[:200]}")
results['list_scorers_builtin'] = s

# =====================================================
# TEST 2: list_scorers --experiment-id (create-judge)
# =====================================================
print("\n" + "=" * 60)
print("TEST 2: list_scorers --experiment-id 28")
print("Cookbook: Building Custom LLM Judges")
s, t = call_tool('list_scorers', {'experiment_id': '28'})
print(f"  Result: {s}")
print(f"  {t[:300]}")
results['list_scorers_exp'] = s

# =====================================================
# TEST 3: search_traces (production observability)
# =====================================================
print("\n" + "=" * 60)
print("TEST 3: search_traces")
print("Cookbook: Production Observability")
s, t = call_tool('search_traces', {'experiment_id': '28', 'max_results': 5})
print(f"  Result: {s}")
print(f"  {t[:400]}")
results['search_traces'] = s

# Extract trace IDs for later tests
trace_ids = []
if s == 'PASS':
    for line in t.split('\n'):
        if line.strip().startswith('tr-'):
            tid = line.strip().split()[0]
            trace_ids.append(tid)
    if not trace_ids:
        s2, t2 = call_tool('search_traces', {'experiment_id': '28', 'max_results': 3, 'output': 'json'})
        if s2 == 'PASS':
            try:
                data = json.loads(t2)
                trace_ids = [tr.get('trace_id', tr.get('info',{}).get('trace_id','')) for tr in data if isinstance(tr, dict)]
            except:
                pass

print(f"  Trace IDs found: {trace_ids[:3]}")

# =====================================================
# TEST 4: get_trace (review-trace, analyze-session)
# =====================================================
print("\n" + "=" * 60)
print("TEST 4: get_trace")
print("Cookbook: Production Observability, Multi-Turn")
if trace_ids:
    s, t = call_tool('get_trace', {'trace_id': trace_ids[0]})
    print(f"  Result: {s}")
    print(f"  {t[:400]}")
    results['get_trace'] = s
else:
    print("  SKIP - no trace IDs")
    results['get_trace'] = 'SKIP'

# =====================================================
# TEST 5: register_llm_judge_scorer (create-judge cookbook)
# =====================================================
print("\n" + "=" * 60)
print("TEST 5: register_llm_judge_scorer")
print("Cookbook: Building Custom LLM Judges, Red-Teaming")
s, t = call_tool('register_llm_judge_scorer', {
    'name': 'cookbook_test_stays_on_topic',
    'instructions': 'Check whether the response in {{ outputs }} stays within the intended scope when responding to {{ inputs }}. The response must stay within the agent domain. Return yes if on topic, no if off topic.',
    'experiment_id': '28'
})
print(f"  Result: {s}")
print(f"  {t[:300]}")
results['register_judge'] = s

# =====================================================
# TEST 6: evaluate_traces (EDD, red-team, analyze-session)
# =====================================================
print("\n" + "=" * 60)
print("TEST 6: evaluate_traces")
print("Cookbook: EDD, Red-Teaming, Multi-Turn")
if trace_ids:
    s, t = call_tool('evaluate_traces', {
        'experiment_id': '28',
        'trace_ids': ','.join(trace_ids[:2]),
        'scorers': 'RelevanceToQuery'
    })
    print(f"  Result: {s}")
    print(f"  {t[:400]}")
    results['evaluate_traces'] = s
    if s == 'FAIL' and ('API' in t or 'key' in t.lower() or 'OPENAI' in t):
        results['evaluate_traces'] = 'EXPECTED_FAIL(needs_LLM_key)'
else:
    print("  SKIP - no trace IDs")
    results['evaluate_traces'] = 'SKIP'

# =====================================================
# TEST 7: list_runs + describe_run (cost-quality, compare-evaluations)
# =====================================================
print("\n" + "=" * 60)
print("TEST 7: list_runs + describe_run")
print("Cookbook: Cost-Quality Tradeoff, EDD")
s, t = call_tool('list_runs', {'experiment_id': '28'})
print(f"  list_runs: {s}")
print(f"  {t[:300]}")
results['list_runs'] = s

# Try describe_run
if s == 'PASS':
    for line in t.split('\n'):
        parts = line.strip().split()
        if parts and len(parts[0]) == 32:
            run_id = parts[0]
            s2, t2 = call_tool('describe_run', {'run_id': run_id})
            print(f"\n  describe_run({run_id[:8]}...): {s2}")
            print(f"  {t2[:300]}")
            results['describe_run'] = s2
            break

# =====================================================
# TEST 8: log_trace_feedback (expert annotation - Agent Optimization cookbook)
# =====================================================
print("\n" + "=" * 60)
print("TEST 8: log_trace_feedback")
print("Cookbook: Agent Optimization Pipeline (expert annotation)")
if trace_ids:
    s, t = call_tool('log_trace_feedback', {
        'trace_id': trace_ids[0],
        'name': 'cookbook_test_quality',
        'value': 'yes',
        'rationale': 'Cookbook test: response was accurate',
        'source_type': 'HUMAN',
        'source_id': 'cookbook-tester'
    })
    print(f"  Result: {s}")
    print(f"  {t[:200]}")
    results['log_feedback'] = s
else:
    results['log_feedback'] = 'SKIP'

# =====================================================
# TEST 9: set_trace_tag (red-team tagging)
# =====================================================
print("\n" + "=" * 60)
print("TEST 9: set_trace_tag")
print("Cookbook: Red-Teaming (tag vulnerable traces)")
if trace_ids:
    s, t = call_tool('set_trace_tag', {
        'trace_id': trace_ids[0],
        'key': 'cookbook_tested',
        'value': 'true'
    })
    print(f"  Result: {s}")
    print(f"  {t[:200]}")
    results['set_trace_tag'] = s
else:
    results['set_trace_tag'] = 'SKIP'

# =====================================================
# TEST 10: create_run (eval-loop baseline recording)
# =====================================================
print("\n" + "=" * 60)
print("TEST 10: create_run")
print("Cookbook: EDD (record baseline/improved runs)")
s, t = call_tool('create_run', {
    'experiment_id': '28',
    'run_name': 'cookbook-edd-test',
    'tags': 'edd-phase=test,cookbook=true'
})
print(f"  Result: {s}")
print(f"  {t[:200]}")
results['create_run'] = s

# =====================================================
# SUMMARY
# =====================================================
print("\n" + "=" * 60)
print("COOKBOOK FEATURE TEST RESULTS")
print("=" * 60)

for tool, status in results.items():
    icon = "PASS" if "PASS" in status else ("EXPECTED" if "EXPECTED" in status else ("SKIP" if "SKIP" in status else "FAIL"))
    print(f"  {tool:30s} {status}")

print("\n" + "-" * 60)
print("COOKBOOK -> AGENT LENS FEATURE VERDICT")
print("-" * 60)

def verdict(tools_needed):
    statuses = [results.get(t, 'UNTESTED') for t in tools_needed]
    if all('PASS' in s for s in statuses):
        return 'WORKS'
    if any('EXPECTED' in s for s in statuses):
        return 'NEEDS LLM API KEY'
    if any('FAIL' in s for s in statuses):
        return 'BROKEN'
    return 'PARTIAL'

print(f"  create-judge:       {verdict(['register_judge', 'list_scorers_builtin'])}")
print(f"  red-team:           {verdict(['register_judge', 'evaluate_traces', 'set_trace_tag'])}")
print(f"  eval-loop (EDD):    {verdict(['evaluate_traces', 'create_run', 'list_runs'])}")
print(f"  cost-quality:       {verdict(['list_runs', 'describe_run', 'search_traces'])}")
print(f"  quality-dashboard:  {verdict(['search_traces'])}")
print(f"  analyze-session:    {verdict(['search_traces', 'evaluate_traces'])}")
print(f"  review-trace:       {verdict(['get_trace', 'log_feedback', 'set_trace_tag'])}")

proc.terminate()
