"use client";

import { useEffect, useMemo, useState } from "react";
import { createAgent, searchRoles, testAgentRuntime } from "@/lib/api";
import type { Agent, AgentRuntimeTestResult, Credential, ModelInfo, Role } from "@/lib/types";
import { ErrorNote } from "./Feedback";

export default function AgentCreateForm({
  models,
  credentials,
  onCreated,
  onCancel,
}: {
  models: ModelInfo[];
  credentials: Credential[];
  onCreated: (agent: Agent) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [role, setRole] = useState<number | null>(null);
  const [model, setModel] = useState<number | null>(models[0]?.id ?? null);
  const [providerId, setProviderId] = useState<number | null>(models[0]?.provider ?? null);
  const [credential, setCredential] = useState<number | null>(null);
  const [roleQuery, setRoleQuery] = useState("");
  const [roles, setRoles] = useState<Role[]>([]);
  const [temperature, setTemperature] = useState(0.4);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AgentRuntimeTestResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchRoles(roleQuery, 50, controller.signal).then((result) => setRoles(result.results)).catch((err) => {
        if ((err as Error).name !== "AbortError") setError(err);
      });
    }, 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [roleQuery]);

  const selectedModel = models.find((item) => item.id === model);
  const providers = useMemo(() => Array.from(new Map(models.map((item) => [item.provider, { id: item.provider, name: item.provider_name || item.provider_key }])).values()), [models]);
  const providerModels = useMemo(() => models.filter((item) => providerId === null || item.provider === providerId), [models, providerId]);
  const compatibleCredentials = useMemo(
    () => credentials.filter((item) => !selectedModel || item.provider === selectedModel.provider),
    [credentials, selectedModel]
  );

  async function runRuntimeTest() {
    setTesting(true); setError(null); setTestResult(null);
    try {
      setTestResult(await testAgentRuntime({ model, credential, prompt, temperature, max_tokens: Math.min(maxTokens, 256) }));
    } catch (err) { setError(err); }
    finally { setTesting(false); }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const agent = await createAgent({
        name: name.trim(),
        title: title.trim(),
        key: key.trim() || undefined,
        description: description.trim(),
        role,
        model,
        credential,
        temperature,
        max_output_tokens: maxTokens,
        context_limit: 8192,
        status: "active",
        is_enabled: true,
        initial_prompt: prompt.trim(),
      });
      onCreated(agent);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="agent-create-form" onSubmit={submit}>
      {error ? <ErrorNote error={error} /> : null}
      <div className="form-section-title"><span>01</span><div><strong>Identity</strong><small>Name this worker and define its responsibility.</small></div></div>
      <div className="row">
        <div className="field"><label>Agent name</label><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Security Review Agent" required autoFocus /></div>
        <div className="field"><label>Custom title</label><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Principal Security Reviewer" /></div>
      </div>
      <div className="field"><label>Key</label><input className="mono" value={key} onChange={(e) => setKey(e.target.value)} placeholder="generated-from-name" /></div>
      <div className="field"><label>Description</label><textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this agent owns and when it should be used…" /></div>

      <div className="form-section-title"><span>02</span><div><strong>Runtime</strong><small>Assign a role, model and generation limits.</small></div></div>
      <div className="field"><label>Find organizational role</label><input value={roleQuery} onChange={(e) => setRoleQuery(e.target.value)} placeholder="Search 2,700+ roles…" /></div>
      <div className="row">
        <div className="field"><label>Organizational role</label><select value={role ?? ""} onChange={(e) => setRole(e.target.value ? Number(e.target.value) : null)}><option value="">No role</option>{roles.map((item) => <option key={item.uuid} value={item.id}>{item.name}</option>)}</select></div>
        <div className="field"><label>Provider / operator</label><select value={providerId ?? ""} onChange={(e) => { const next = e.target.value ? Number(e.target.value) : null; setProviderId(next); setModel(models.find((item) => item.provider === next)?.id ?? null); setCredential(null); setTestResult(null); }}><option value="">Select provider</option>{providers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
      </div>
      <div className="field"><label>Model</label><select value={model ?? ""} onChange={(e) => { setModel(e.target.value ? Number(e.target.value) : null); setCredential(null); setTestResult(null); }}><option value="">Select model</option>{providerModels.map((item) => <option key={item.uuid} value={item.id}>{item.name} · {item.remote_id || item.key}</option>)}</select><div className="hint">Enter or import exact remote model IDs from Providers &amp; models.</div></div>
      <div className="field"><label>Provider credential</label><select value={credential ?? ""} onChange={(e) => setCredential(e.target.value ? Number(e.target.value) : null)}><option value="">No credential / local endpoint</option>{compatibleCredentials.map((item) => <option key={item.uuid} value={item.id}>{item.provider_name} · {item.label} · {item.secret_hint}</option>)}</select><div className="hint">Only credentials belonging to the selected model provider are shown.</div></div>
      <div className="row">
        <div className="field"><label>Temperature <span className="field-value">{temperature.toFixed(2)}</span></label><input type="range" min={0} max={2} step={0.05} value={temperature} onChange={(e) => setTemperature(Number(e.target.value))} /></div>
        <div className="field"><label>Max output tokens</label><input type="number" min={1} value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} /></div>
      </div>

      <div className="form-section-title"><span>03</span><div><strong>System instruction</strong><small>Optional. Taxonomy agents intentionally start without a prompt.</small></div></div>
      <div className="field"><label>System prompt (optional)</label><textarea className="prompt-editor" rows={8} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Leave empty or define a specialist instruction…" /></div>
      <div className="runtime-test-box"><div><strong>Connection test</strong><small>Runs a real low-token request with the selected provider, key and model.</small></div><button className="btn" type="button" onClick={runRuntimeTest} disabled={testing || !model}>{testing ? "Testing…" : "Test runtime"}</button>{testResult ? <div className="runtime-test-result ok"><strong>{testResult.provider} · {testResult.model}</strong><span>{testResult.text}</span><small>{testResult.latency_ms} ms · {testResult.usage?.total_tokens || 0} tokens · ${Number(testResult.cost || 0).toFixed(6)}</small></div> : null}</div>
      <div className="modal-actions"><button className="btn" type="button" onClick={onCancel}>Cancel</button><button className="btn primary" type="submit" disabled={busy}>{busy ? "Creating…" : "Create agent"}</button></div>
    </form>
  );
}
