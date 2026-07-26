import React from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

function Hero() {
  return (
    <section className="hero-section">
      <div className="container">
        <div className="hero-badge">16 skills · 19 MCP tools · 14 verified end-to-end on OpenShift 4.18</div>
        <h1 className="hero-title">
          Trust your agents.<br />Verify with evidence.
        </h1>
        <p className="hero-subtitle">
          Agent Lens is the conversational quality gate for MLflow.
          Evaluate, qualify, and govern your agent fleet — in plain English.
        </p>
        <div className="hero-buttons">
          <Link className="btn-primary" to="/docs/">
            Get Started
          </Link>
          <Link className="btn-secondary" href="https://github.com/rrbanda/agent-lens">
            GitHub
          </Link>
        </div>
      </div>
    </section>
  );
}

function Terminal() {
  return (
    <section className="terminal-section">
      <div className="container">
        <p className="section-label">Quickstart</p>
        <h2 className="section-title">Up and running in minutes.</h2>
        <div className="terminal">
          <div className="terminal-header">
            <span className="terminal-dot terminal-dot--red"></span>
            <span className="terminal-dot terminal-dot--yellow"></span>
            <span className="terminal-dot terminal-dot--green"></span>
          </div>
          <div className="terminal-body">
            <div className="terminal-line">
              <span className="terminal-comment"># Clone and verify locally</span>
            </div>
            <div className="terminal-line">
              <span className="terminal-prompt">$ </span>
              <span className="terminal-command">git clone https://github.com/rrbanda/agent-lens && cd agent-lens</span>
            </div>
            <div className="terminal-line">
              <span className="terminal-prompt">$ </span>
              <span className="terminal-command">make dev-setup && make mlflow-start</span>
            </div>
            <div className="terminal-line">
              <span className="terminal-prompt">$ </span>
              <span className="terminal-command">make seed-data && make test-integration</span>
            </div>
            <div className="terminal-line">
              <span className="terminal-output">41 passed in 12.4s</span>
            </div>
            <br />
            <div className="terminal-line">
              <span className="terminal-comment"># Deploy to OpenShift</span>
            </div>
            <div className="terminal-line">
              <span className="terminal-prompt">$ </span>
              <span className="terminal-command">make deploy-all && make status</span>
            </div>
            <div className="terminal-line">
              <span className="terminal-output">agent-lens   1/1   Running   0   49s</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const features = [
  {
    icon: '🔍',
    title: 'Conversational Evaluation',
    description: 'Ask "Can this agent be deployed?" and get a structured qualification verdict with evidence. No Python scripts required.',
  },
  {
    icon: '⚡',
    title: 'MLflow MCP Native',
    description: 'Built entirely on the official MLflow MCP server. 19 tools from mlflow[mcp] 3.14, zero custom forks. Your data stays in MLflow.',
  },
  {
    icon: '🛡️',
    title: 'Red-Team Safety',
    description: 'Test for prompt injection, data exfiltration, jailbreaks, and PII leakage with attack-specific judges.',
  },
  {
    icon: '📊',
    title: 'EDD Loop',
    description: 'Evaluation-Driven Development: baseline, diagnose failures, fix, re-evaluate, compare. The full MLflow cookbook workflow — conversational.',
  },
  {
    icon: '⚖️',
    title: 'Cost-Quality Tradeoff',
    description: 'Compare quality vs cost across models and configurations. Find the optimal tradeoff for your budget.',
  },
  {
    icon: '🧪',
    title: 'Custom Judges',
    description: 'Create domain-specific LLM judges from natural language. "Check if the agent mentions our privacy policy" becomes a registered scorer.',
  },
  {
    icon: '🏷️',
    title: 'Qualification Verdicts',
    description: '>=80% scorer pass rate + <5% error rate = QUALIFIED. Evidence-based decisions, not gut feelings.',
  },
  {
    icon: '✅',
    title: 'Production Verified',
    description: '14 of 16 skills verified end-to-end on OpenShift 4.18 with Hermes v0.19 + MLflow MCP 3.14 against live data.',
  },
];

function Features() {
  return (
    <section className="features-section">
      <div className="container">
        <p className="section-label">Features</p>
        <h2 className="section-title">Everything you need to<br />qualify your agent fleet.</h2>
        <div className="features-grid">
          {features.map((f, i) => (
            <div className="feature-card" key={i}>
              <div className="feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Skills() {
  const skills = [
    { name: 'trace-explorer', tools: 'search_experiments, search_traces, get_trace', desc: 'Search and drill into any trace', status: 'PASS' },
    { name: 'quality-dashboard', tools: 'search_experiments, search_traces, list_runs', desc: 'Fleet-wide health + cost + latency', status: 'PASS' },
    { name: 'analyze-session', tools: 'search_traces, get_trace', desc: 'Trace analysis with status and latency', status: 'PASS' },
    { name: 'review-trace', tools: 'get_trace, get_trace_assessment', desc: 'Deep-dive + assessments', status: 'PASS' },
    { name: 'create-regression', tools: 'update_trace_assessment, set_trace_tag', desc: 'Flag failures for follow-up', status: 'PASS' },
    { name: 'evaluate-agent', tools: 'list_scorers, evaluate_traces', desc: 'Run LLM judges on traces', status: 'PARTIAL' },
    { name: 'compare-evaluations', tools: 'list_runs, describe_run', desc: 'Track quality over time', status: 'PASS' },
    { name: 'create-judge', tools: 'list_scorers, register_llm_judge_scorer', desc: 'Build custom scorers from English', status: 'PASS' },
    { name: 'red-team', tools: 'search_traces, evaluate_traces', desc: 'Adversarial safety evaluation', status: 'PARTIAL' },
    { name: 'eval-loop', tools: 'create_run, search_traces', desc: 'Full EDD improvement cycle', status: 'PASS' },
    { name: 'cost-quality', tools: 'list_runs, describe_run, search_traces', desc: 'Cost vs quality tradeoff analysis', status: 'PASS' },
    { name: 'audit-trail', tools: 'search_traces, list_runs, describe_run', desc: 'Qualification decision history', status: 'PASS' },
    { name: 'agent-registry', tools: 'search_experiments, list_runs, describe_run', desc: 'Fleet inventory and status', status: 'PASS' },
    { name: 'executive-summary', tools: 'search_experiments, search_traces, list_runs', desc: 'Board-ready health summary', status: 'PASS' },
    { name: 'compliance-export', tools: 'search_traces, list_runs, describe_run', desc: 'JSONL/CSV export for GRC tools', status: 'PASS*' },
    { name: 'aggregate-traces', tools: 'search_traces', desc: 'Error rates, latency, token trends', status: 'PARTIAL' },
  ];

  return (
    <section className="skills-section">
      <div className="container">
        <p className="section-label">Skills</p>
        <h2 className="section-title">16 skills. 12 fully verified.</h2>
        <div className="skills-table">
          <table>
            <thead>
              <tr>
                <th>Skill</th>
                <th>MCP Tools</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {skills.map((s, i) => (
                <tr key={i}>
                  <td><strong>{s.name}</strong><br /><span style={{color: '#64748b', fontSize: '0.85rem'}}>{s.desc}</span></td>
                  <td><code style={{fontSize: '0.8rem'}}>{s.tools}</code></td>
                  <td className={s.status === 'PASS' ? 'status-pass' : s.status === 'PARTIAL' ? 'status-partial' : 'status-pass'}>{s.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="cta-section">
      <div className="container">
        <h2 className="cta-title">Stop guessing if your agents work.</h2>
        <p className="cta-subtitle">
          Open source. Self-hosted. Runs on any Kubernetes cluster with MLflow.
        </p>
        <div className="hero-buttons">
          <Link className="btn-primary" href="https://github.com/rrbanda/agent-lens">
            Star on GitHub
          </Link>
          <Link className="btn-secondary" to="/docs/">
            Read the docs →
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home(): React.JSX.Element {
  return (
    <Layout title="Home" description="Trust your agents. Verify with evidence — conversationally, on MLflow.">
      <Hero />
      <Terminal />
      <Features />
      <Skills />
      <CTA />
    </Layout>
  );
}
