"use client";

import { useEffect, useMemo, useState } from "react";
import type { Agent, AgentRuntimeTestResult, Credential, KnowledgeSource, ModelInfo } from "@/lib/types";
import { createKnowledgeSource, deleteKnowledgeSource, listKnowledgeSources, testAgentRuntime, updateAgent, updateAgentPrompt } from "@/lib/api";
import { ErrorNote } from "./Feedback";

// The agent configuration panel — the DoD screen where a user edits an agent's
// prompt, model and runtime knobs. Config and prompt save through separate API
// calls (the prompt action creates a new immutable PromptVersion server-side).
export default function AgentEditor({
  agent,
  models,
  credentials,
  onSaved,
}: {
  agent: Agent;
  models: ModelInfo[];
  credentials: Credential[];
  onSaved: (updated: Agent) => void;
}) {
  const [name, setName] = useState(agent.name);
  const [title, setTitle] = useState(agent.title || "");
  const [description, setDescription] = useState(agent.description);
  const [temperature, setTemperature] = useState(agent.temperature);
  const [maxTokens, setMaxTokens] = useState(agent.max_output_tokens);
  const [modelId, setModelId] = useState<number | null>(agent.model);
  const [providerId, setProviderId] = useState<number | null>(models.find((item) => item.id === agent.model)?.provider ?? null);
  const [credentialId, setCredentialId] = useState<number | null>(agent.credential);
  const [status, setStatus] = useState(agent.status);
  const [enabled, setEnabled] = useState(agent.is_enabled);
  const [prompt, setPrompt] = useState(agent.system_prompt);

  const [savingConfig, setSavingConfig] = useState(false);
  const [savingPrompt, setSavingPrompt] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AgentRuntimeTestResult | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeSource[]>([]);
  const [knowledgeName, setKnowledgeName] = useState("");
  const [knowledgeContent, setKnowledgeContent] = useState("");
  const [savingKnowledge, setSavingKnowledge] = useState(false);
  const selectedModel = models.find((item) => item.id === modelId);
  const providers = useMemo(() => Array.from(new Map(models.map((item) => [item.provider, { id: item.provider, name: item.provider_name || item.provider_key }])).values()), [models]);
  const providerModels = useMemo(() => models.filter((item) => providerId === null || item.provider === providerId), [models, providerId]);
  const compatibleCredentials = useMemo(
    () => credentials.filter((item) => !selectedModel || item.provider === selectedModel.provider),
    [credentials, selectedModel]
  );

  useEffect(() => { listKnowledgeSources(agent.uuid).then(setKnowledge).catch(setError); }, [agent.uuid]);

  async function runRuntimeTest() {
    setTesting(true); setError(null); setTestResult(null);
    try { setTestResult(await testAgentRuntime({ model: modelId, credential: credentialId, prompt, temperature, max_tokens: Math.min(maxTokens, 256) })); }
    catch (e) { setError(e); }
    finally { setTesting(false); }
  }

  async function saveConfig() {
    setSavingConfig(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateAgent(agent.uuid, {
        name,
        title,
        description,
        temperature,
        max_output_tokens: maxTokens,
        model: modelId,
        credential: credentialId,
        status,
        is_enabled: enabled,
      });
      onSaved({ ...updated, system_prompt: prompt });
      setNotice("Configuration saved.");
    } catch (e) {
      setError(e);
    } finally {
      setSavingConfig(false);
    }
  }

  async function addKnowledge() {
    if (!knowledgeName.trim() || !knowledgeContent.trim()) return;
    setSavingKnowledge(true); setError(null);
    try {
      const source = await createKnowledgeSource({ agent: agent.uuid, name: knowledgeName.trim(), kind: "text", content: knowledgeContent.trim() });
      setKnowledge((current) => [source, ...current]); setKnowledgeName(""); setKnowledgeContent("");
    } catch (e) { setError(e); }
    finally { setSavingKnowledge(false); }
  }

  async function removeKnowledge(uuid: string) {
    try { await deleteKnowledgeSource(uuid); setKnowledge((current) => current.filter((item) => item.uuid !== uuid)); }
    catch (e) { setError(e); }
  }

  async function savePrompt() {
    if (!prompt.trim()) {
      setError(new Error("System prompt cannot be empty."));
      return;
    }
    setSavingPrompt(true);
    setError(null);
    setNotice(null);
    try {
      const res = await updateAgentPrompt(agent.uuid, prompt);
      onSaved({ ...agent, system_prompt: res.content });
      setNotice(`Prompt saved as version v${res.version}.`);
    } catch (e) {
      setError(e);
    } finally {
      setSavingPrompt(false);
    }
  }

  return (
    <div>
      {error ? <ErrorNote error={error} /> : null}
      {notice ? (
        <div
          className="badge ok"
          style={{ marginBottom: "1rem", display: "inline-flex" }}
        >
          {notice}
        </div>
      ) : null}

      <div className="form-section-title"><span>01</span><div><strong>Identity</strong><small>Use a custom name, title and responsibility for this agent.</small></div></div>
      <div className="row"><div className="field"><label>Name</label><input value={name} onChange={(e) => setName(e.target.value)} /></div><div className="field"><label>Custom title</label><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Principal AI Engineer" /></div></div>
      <div className="field"><label>Description</label><textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} /></div>

      <div className="form-section-title"><span>02</span><div><strong>Runtime</strong><small>Provider, model, encrypted credential and generation controls.</small></div></div>

      <div className="row">
        <div className="field">
          <label>Provider / operator</label>
          <select value={providerId ?? ""} onChange={(e) => { const next = e.target.value ? Number(e.target.value) : null; setProviderId(next); setModelId(models.find((item) => item.provider === next)?.id ?? null); setCredentialId(null); setTestResult(null); }}>
            <option value="">Select provider</option>{providers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Model</label>
          <select
            value={modelId ?? ""}
            onChange={(e) =>
              { setModelId(e.target.value ? Number(e.target.value) : null); setCredentialId(null); }
            }
          >
            <option value="">— none —</option>
            {providerModels.map((m) => (
              <option key={m.uuid} value={m.id}>
                {m.name} ({m.provider_name || m.provider_key})
              </option>
            ))}
          </select>
          <div className="hint">Provider: {selectedModel?.provider_name || agent.provider_name || agent.provider || "—"}</div>
        </div>
        <div className="field">
          <label>Status</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">active</option>
            <option value="disabled">disabled</option>
            <option value="draft">draft</option>
          </select>
        </div>
      </div>

      <div className="field">
        <label>Provider credential</label>
        <select value={credentialId ?? ""} onChange={(e) => setCredentialId(e.target.value ? Number(e.target.value) : null)}>
          <option value="">No credential / local endpoint</option>
          {compatibleCredentials.map((credential) => (
            <option key={credential.uuid} value={credential.id}>{credential.provider_name} · {credential.label} · {credential.secret_hint}</option>
          ))}
        </select>
        <div className="hint">Secrets stay encrypted and are never returned to the browser.</div>
      </div>

      <div className="row">
        <div className="field">
          <label>Temperature: {temperature.toFixed(2)}</label>
          <input
            type="range"
            min={0}
            max={2}
            step={0.05}
            value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label>Max output tokens</label>
          <input
            type="number"
            min={1}
            value={maxTokens}
            onChange={(e) => setMaxTokens(Number(e.target.value))}
          />
        </div>
      </div>

      <div className="field">
        <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input
            type="checkbox"
            style={{ width: "auto" }}
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          Enabled
        </label>
      </div>

      <div style={{ margin: "0.5rem 0 1rem" }}>
        <button className="btn" onClick={saveConfig} disabled={savingConfig}>
          {savingConfig ? "Saving…" : "Save config"}
        </button>
      </div>

      <div className="runtime-test-box"><div><strong>Live runtime test</strong><small>Uses the current provider, encrypted key and exact model before saving.</small></div><button className="btn" type="button" onClick={runRuntimeTest} disabled={testing || !modelId}>{testing ? "Testing…" : "Test now"}</button>{testResult ? <div className="runtime-test-result ok"><strong>{testResult.provider} · {testResult.model}</strong><span>{testResult.text}</span><small>{testResult.latency_ms} ms · {testResult.usage?.total_tokens || 0} tokens · ${Number(testResult.cost || 0).toFixed(6)}</small></div> : null}</div>

      <div className="field">
        <label>System prompt</label>
        <textarea
          rows={14}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="This agent's system prompt…"
        />
        <div className="hint">
          Saving creates a new immutable prompt version on the server (history is
          preserved).
        </div>
      </div>
      <button className="btn primary" onClick={savePrompt} disabled={savingPrompt}>
        {savingPrompt ? "Saving prompt…" : "Save prompt"}
      </button>

      <div className="form-section-title"><span>03</span><div><strong>Knowledge sources</strong><small>Reusable context stays separate from the system prompt.</small></div></div>
      <div className="knowledge-editor"><div className="field"><label>Source name</label><input value={knowledgeName} onChange={(e) => setKnowledgeName(e.target.value)} placeholder="e.g. Product policies" /></div><div className="field"><label>Text knowledge</label><textarea rows={5} value={knowledgeContent} onChange={(e) => setKnowledgeContent(e.target.value)} placeholder="Paste policies, domain facts, SOPs or project context…" /></div><button className="btn" type="button" onClick={addKnowledge} disabled={savingKnowledge || !knowledgeName.trim() || !knowledgeContent.trim()}>{savingKnowledge ? "Adding…" : "Add knowledge"}</button><div className="knowledge-list">{knowledge.map((source) => <div key={source.uuid}><span><strong>{source.name}</strong><small>{source.kind} · {source.content.length.toLocaleString()} chars</small></span><button onClick={() => removeKnowledge(source.uuid)} aria-label={`Delete ${source.name}`}>×</button></div>)}</div></div>
    </div>
  );
}
