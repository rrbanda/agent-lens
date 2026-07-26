import React from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

function Hero() {
  return (
    <section className="hero-section">
      <div className="container">
        <div className="hero-badge">Verified on OpenShift with MLflow MCP 3.14</div>
        <h1 className="hero-title">
          Qualify AI agents<br />you didn't build.
        </h1>
        <p className="hero-subtitle">
          Agent Lens is the conversational qualification layer for MLflow.
          Evaluate, certify, and govern your agent fleet — in plain English.
        </p>
        <div className="hero-buttons">
          <Link className="btn-primary" to="/docs/">
            Get Started
          </Link>
          <Link className="btn-secondary" href="https://github.com/rrbanda/agentlens">
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
              <span className="terminal-command">git clone https://github.com/rrbanda/agentlens && cd agentlens</span>
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
              <span className="terminal-output">41 passed, 1 skipped in 12.4s</span>
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
    description: 'Built entirely on the official MLflow MCP server. 11 tools, zero custom forks. Your data stays in MLflow.',
  },
  {
    icon: '🛡️',
    title: 'Fleet Observatory',
    description: 'See all your agents in one view. HEALTHY, WARNING, CRITICAL, INACTIVE. Error rates, latency, pass rates at a glance.',
  },
  {
    icon: '📊',
    title: 'Qualification Verdicts',
    description: '≥80% scorer pass rate + <5% error rate = QUALIFIED. Evidence-based decisions, not gut feelings.',
  },
  {
    icon: '🏷️',
    title: 'Regression Tracking',
    description: 'Flag bad traces, log expectations, tag regressions. Build a dataset of failures for re-evaluation.',
  },
  {
    icon: '✅',
    title: 'Production Verified',
    description: 'Tested end-to-end on OpenShift 4.18 with Hermes v0.19. 41 integration tests against real MLflow data.',
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
    { name: 'trace-explorer', tools: 'search_experiments, search_traces, get_trace', desc: 'Search and drill into any trace' },
    { name: 'quality-dashboard', tools: 'search_experiments, search_traces, list_runs', desc: 'Fleet-wide health overview' },
    { name: 'analyze-session', tools: 'search_traces', desc: 'Multi-turn session forensics' },
    { name: 'review-trace', tools: 'get_trace, log_trace_feedback, set_trace_tag', desc: 'Deep-dive + human annotation' },
    { name: 'create-regression', tools: 'get_trace, log_trace_expectation, set_trace_tag', desc: 'Flag failures for follow-up' },
    { name: 'evaluate-agent', tools: 'list_scorers, evaluate_traces', desc: 'Run LLM judges on traces' },
    { name: 'compare-evaluations', tools: 'list_runs, describe_run', desc: 'Track quality over time' },
  ];

  return (
    <section className="skills-section">
      <div className="container">
        <p className="section-label">Skills</p>
        <h2 className="section-title">7 skills. All verified.</h2>
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
                  <td className="status-pass">PASS</td>
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
          <Link className="btn-primary" href="https://github.com/rrbanda/agentlens">
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
    <Layout title="Home" description="Qualify AI agents you didn't build — conversationally, on MLflow.">
      <Hero />
      <Terminal />
      <Features />
      <Skills />
      <CTA />
    </Layout>
  );
}
