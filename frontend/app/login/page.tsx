"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import { ErrorNote } from "@/components/Feedback";
import Icon from "@/components/Icon";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // Already signed in? Skip straight to the dashboard.
  useEffect(() => {
    if (isAuthenticated()) router.replace("/dashboard");
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-shell">
        <section className="login-story">
          <div className="login-brand"><span className="brand-mark"><Icon name="spark" /></span> easy<span>ES</span></div>
          <div className="login-story-copy">
            <div className="eyebrow"><span className="live-dot" /> AI-native execution platform</div>
            <h1>Run the company.<br /><span>Watch intelligence work.</span></h1>
            <p>One control plane for your people, AI agents, workflows, decisions and delivery.</p>
            <div className="login-features">
              <div><Icon name="workflow" /><span><strong>Durable workflows</strong><small>Real conditions, loops and quality gates</small></span></div>
              <div><Icon name="agents" /><span><strong>Specialist AI workforce</strong><small>Independent models, prompts and budgets</small></span></div>
              <div><Icon name="pulse" /><span><strong>Live observability</strong><small>Every action, artifact and decision in view</small></span></div>
            </div>
          </div>
          <div className="login-proof"><span className="proof-avatars"><i>A</i><i>PM</i><i>QA</i></span><span><strong>10 agents online</strong><small>Ready for the next mission</small></span></div>
        </section>
        <section className="login-form-side">
          <form className="login-card" onSubmit={submit}>
            <div className="login-mobile-brand"><span className="brand-mark"><Icon name="spark" /></span> easyES</div>
            <div className="eyebrow">Welcome back</div>
            <h2>Sign in to your command center</h2>
            <div className="tag">Enter your workspace credentials to continue.</div>
            {error ? <ErrorNote error={error} /> : null}
            <div className="field"><label>Username</label><input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter username" autoFocus autoComplete="username" /></div>
            <div className="field"><label>Password</label><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter password" autoComplete="current-password" /></div>
            <button className="btn primary big login-submit" type="submit" disabled={busy}>{busy ? <><span className="spinner" /> Signing in…</> : <>Enter workspace <Icon name="arrow" /></>}</button>
            <div className="demo-credentials"><Icon name="shield" /><span><strong>Demo access</strong><small><span className="mono">amin</span> / <span className="mono">123456</span></small></span></div>
          </form>
        </section>
      </div>
    </div>
  );
}
