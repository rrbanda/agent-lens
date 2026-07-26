import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary')} style={{padding: '4rem 0'}}>
      <div className="container">
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div style={{display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '2rem'}}>
          <Link className="button button--secondary button--lg" to="/docs/">
            Get Started
          </Link>
          <Link className="button button--outline button--lg" to="/docs/skills"
            style={{color: 'white', borderColor: 'white'}}>
            View Skills
          </Link>
        </div>
      </div>
    </header>
  );
}

const features = [
  {
    title: 'Conversational Evaluation',
    description: 'Evaluate agents by asking questions in plain English. No Python scripts required.',
  },
  {
    title: 'MLflow MCP Native',
    description: 'Built on the official MLflow MCP server. 11 tools, zero custom forks.',
  },
  {
    title: '7 Verified Skills',
    description: 'Trace exploration, quality dashboards, reviews, regressions, and evaluations — all tested end-to-end.',
  },
  {
    title: 'Fleet-Wide Visibility',
    description: 'See all your agents\' health in one view. HEALTHY, WARNING, CRITICAL, INACTIVE.',
  },
  {
    title: 'Qualification Verdicts',
    description: '≥80% pass rate + <5% error rate = QUALIFIED. Evidence-based, not gut feelings.',
  },
  {
    title: 'Production Ready',
    description: 'Runs on OpenShift with Hermes v0.19. 41 integration tests. Zero vaporware.',
  },
];

function Feature({title, description}: {title: string; description: string}) {
  return (
    <div className={clsx('col col--4')} style={{marginBottom: '2rem'}}>
      <div className="padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function Home(): React.JSX.Element {
  return (
    <Layout title="Home" description="Qualify AI agents you didn't build — conversationally, on MLflow.">
      <HomepageHeader />
      <main>
        <section style={{padding: '4rem 0'}}>
          <div className="container">
            <div className="row">
              {features.map((props, idx) => (
                <Feature key={idx} {...props} />
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
