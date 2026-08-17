import Link from "next/link";
import Icon from "@/components/Icon";

const proof = [
  ["Roles", "161+"],
  ["Provider catalog", "148"],
  ["Workflow loop", "QA -> fix"],
];

const capabilities = [
  ["Model", "Companies, units, roles, people, agents, tools, policies, and budgets."],
  ["Execute", "Graph workflows with typed nodes, conditions, approvals, retries, and artifacts."],
  ["Improve", "Evaluation and QA feedback loops turn failed work into bounded corrections."],
];

export default function LandingPage() {
  return (
    <main className="landing-page">
      <nav className="landing-nav" aria-label="Landing navigation">
        <Link href="/" className="landing-brand">
          <span className="brand-mark"><Icon name="spark" /></span>
          <span>easy<span>ES</span></span>
        </Link>
        <div className="landing-nav-actions">
          <Link href="/login" className="btn compact">Sign in</Link>
          <Link href="/dashboard" className="btn primary compact">Open app</Link>
        </div>
      </nav>

      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="eyebrow"><span className="live-dot" /> AI-native execution system</div>
          <h1>easyES</h1>
          <p>
            A control room for designing and running a Human + AI organization:
            roles, agents, workflows, provider routing, live executions, and QA feedback loops.
          </p>
          <div className="landing-actions">
            <Link href="/login" className="btn primary big">Enter workspace <Icon name="arrow" /></Link>
            <Link href="/dashboard" className="btn big">View dashboard</Link>
          </div>
        </div>

        <div className="landing-console" aria-label="easyES execution preview">
          <div className="console-top">
            <span>execution://software-delivery</span>
            <strong>live</strong>
          </div>
          <div className="console-flow">
            <span>Idea</span>
            <span>Research</span>
            <span>Plan</span>
            <span>Build</span>
            <span>QA</span>
            <span>Fix</span>
          </div>
          <div className="console-grid">
            <div>
              <small>Agent</small>
              <strong>Developer Agent</strong>
              <span>receiving QA feedback</span>
            </div>
            <div>
              <small>Status</small>
              <strong>iteration 2</strong>
              <span>tests passing</span>
            </div>
            <div>
              <small>Gateway</small>
              <strong>fake/local</strong>
              <span>vendor-neutral route</span>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-proof" aria-label="Project facts">
        {proof.map(([label, value]) => (
          <div key={label}>
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </section>

      <section className="landing-capabilities">
        {capabilities.map(([title, body]) => (
          <article key={title}>
            <span className="cap-dot" />
            <h2>{title}</h2>
            <p>{body}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
