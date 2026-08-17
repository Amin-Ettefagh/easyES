"use client";

import { useEffect, useMemo, useState } from "react";
import {
  connectProvider,
  getProviderCatalog,
  listProviders,
  syncProviderModels,
  testProvider,
  type ConnectProviderInput,
} from "@/lib/api";
import type { ModelProvider, ProviderCatalogEntry } from "@/lib/types";
import Modal from "@/components/Modal";
import Icon from "@/components/Icon";
import { ErrorNote, Loading } from "@/components/Feedback";

const GENERIC_CONFIG = {
  method: "POST",
  path: "/v1/chat/completions",
  request_template: {
    model: "{{model}}",
    messages: "{{messages}}",
    temperature: "{{temperature}}",
    max_tokens: "{{max_tokens}}",
  },
  response_path: "choices.0.message.content",
  models_path: "/v1/models",
  models_response_path: "data",
};

function ConnectProviderForm({ entry, existing, onDone, onCancel }: {
  entry: ProviderCatalogEntry;
  existing?: ModelProvider;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [key, setKey] = useState(existing?.key || entry.key);
  const [name, setName] = useState(existing?.name || entry.name);
  const [baseUrl, setBaseUrl] = useState(existing?.base_url || entry.base_url);
  const [modelId, setModelId] = useState("");
  const [contextWindow, setContextWindow] = useState(8192);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [advanced, setAdvanced] = useState(JSON.stringify(
    existing?.config && Object.keys(existing.config).length
      ? existing.config
      : entry.key === "custom-rest"
        ? GENERIC_CONFIG
        : {},
    null,
    2,
  ));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      let config: Record<string, unknown> = {};
      if (advanced.trim()) config = JSON.parse(advanced);
      const credentials = Object.fromEntries(Object.entries(secrets).filter(([, value]) => value.trim() !== ""));
      const input: ConnectProviderInput = {
        catalog_key: entry.key,
        key: key.trim(),
        name: name.trim(),
        base_url: baseUrl.trim(),
        credentials,
        config,
        model_id: modelId.trim() || undefined,
        model_name: modelId.trim() || undefined,
        context_window: contextWindow,
        max_output_tokens: maxTokens,
      };
      await connectProvider(input);
      onDone();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="provider-connect-form" onSubmit={submit}>
      {error ? <ErrorNote error={error} /> : null}
      <div className="provider-form-intro">
        <span className="provider-logo"><Icon name="provider" /></span>
        <div><strong>{entry.name}</strong><span>{entry.capabilities.join(" · ")} · {entry.adapter.replaceAll("_", " ")}</span></div>
        {entry.docs_url ? <a className="btn" href={entry.docs_url} target="_blank" rel="noreferrer">Official docs ↗</a> : null}
      </div>

      <div className="form-section-title"><span>01</span><div><strong>Connection</strong><small>Endpoint and local identity for this provider instance.</small></div></div>
      <div className="row">
        <div className="field"><label>Connection name</label><input value={name} onChange={(event) => setName(event.target.value)} required /></div>
        <div className="field"><label>Local key</label><input className="mono" value={key} onChange={(event) => setKey(event.target.value)} required /></div>
      </div>
      <div className="field"><label>Base URL {entry.local ? "(reachable from Docker)" : ""}</label><input className="mono" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder={entry.adapter === "bedrock" || entry.adapter === "vertex" ? "Managed by cloud SDK — optional" : "https://api.provider.com/v1"} /><div className="hint">For services running on this computer use <span className="mono">host.docker.internal</span>, not localhost.</div></div>

      <div className="form-section-title"><span>02</span><div><strong>Credentials</strong><small>Encrypted server-side; existing values are never loaded back into this form.</small></div></div>
      <div className="provider-secret-grid">
        {entry.credential_fields.map((field) => <div className="field" key={field.key}><label>{field.label}</label>{field.multiline ? <textarea className="mono" rows={5} value={secrets[field.key] || ""} onChange={(event) => setSecrets((current) => ({ ...current, [field.key]: event.target.value }))} placeholder={existing ? "Leave empty to keep current value" : field.required ? "Required" : "Optional"} /> : <input type={field.secret ? "password" : "text"} value={secrets[field.key] || ""} onChange={(event) => setSecrets((current) => ({ ...current, [field.key]: event.target.value }))} placeholder={existing ? "Leave empty to keep current value" : field.required ? "Required" : "Optional"} />}</div>)}
      </div>

      <div className="form-section-title"><span>03</span><div><strong>First model</strong><small>Optional. Add an exact vendor model ID now or discover models after connecting.</small></div></div>
      <div className="row">
        <div className="field"><label>Remote model ID</label><input className="mono" value={modelId} onChange={(event) => setModelId(event.target.value)} placeholder="owner/model-name or deployment ID" /></div>
        <div className="field"><label>Context window</label><input type="number" min={1} value={contextWindow} onChange={(event) => setContextWindow(Number(event.target.value))} /></div>
        <div className="field"><label>Max output</label><input type="number" min={1} value={maxTokens} onChange={(event) => setMaxTokens(Number(event.target.value))} /></div>
      </div>

      <details className="provider-advanced" open={entry.adapter === "generic_rest"}>
        <summary>Advanced adapter configuration</summary>
        <div className="field"><label>JSON transport contract</label><textarea className="mono" rows={12} value={advanced} onChange={(event) => setAdvanced(event.target.value)} /><div className="hint">Custom REST supports request templates, response paths, headers and async polling without changing backend code.</div></div>
      </details>

      <div className="modal-actions"><button type="button" className="btn" onClick={onCancel}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? "Saving encrypted connection…" : existing ? "Update connection" : "Connect provider"}</button></div>
    </form>
  );
}

export default function ProvidersPage() {
  const [catalog, setCatalog] = useState<ProviderCatalogEntry[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [selected, setSelected] = useState<ProviderCatalogEntry | null>(null);
  const [editing, setEditing] = useState<ModelProvider | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [notices, setNotices] = useState<Record<string, string>>({});
  const [discovered, setDiscovered] = useState<Record<string, Array<{ id: string; name: string }>>>({});

  async function reloadProviders() {
    setProviders(await listProviders());
  }

  useEffect(() => {
    Promise.all([getProviderCatalog(), listProviders()])
      .then(([catalogResult, connected]) => { setCatalog(catalogResult.results); setCategories(catalogResult.categories); setProviders(connected); })
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => catalog.filter((entry) => (!category || entry.category === category) && (!search || `${entry.name} ${entry.key} ${entry.capabilities.join(" ")}`.toLowerCase().includes(search.toLowerCase()))), [catalog, category, search]);

  async function verify(provider: ModelProvider) {
    setNotices((current) => ({ ...current, [provider.uuid]: "Checking credentials and model endpoint…" }));
    try {
      const result = await testProvider(provider.uuid);
      setDiscovered((current) => ({ ...current, [provider.uuid]: result.models || [] }));
      setNotices((current) => ({ ...current, [provider.uuid]: result.model_count ? `Connected · ${result.model_count} models discovered` : "Connected · discovery is not exposed by this adapter" }));
    } catch (err) {
      setNotices((current) => ({ ...current, [provider.uuid]: err instanceof Error ? err.message : "Connection failed" }));
    }
  }

  async function importModels(provider: ModelProvider) {
    const rows = discovered[provider.uuid] || [];
    if (!rows.length) return;
    try {
      const result = await syncProviderModels(provider.uuid, rows);
      setNotices((current) => ({ ...current, [provider.uuid]: `${result.count} models imported into the organization registry` }));
      await reloadProviders();
    } catch (err) {
      setNotices((current) => ({ ...current, [provider.uuid]: err instanceof Error ? err.message : "Model import failed" }));
    }
  }

  function configure(provider: ModelProvider) {
    const catalogKey = String(provider.config?.catalog_key || "custom-rest");
    const entry = catalog.find((item) => item.key === catalogKey) || catalog.find((item) => item.key === "custom-rest") || null;
    setEditing(provider);
    setSelected(entry);
  }

  if (loading) return <Loading label="Loading provider catalogue…" />;

  return (
    <div>
      <div className="page-head"><div><div className="eyebrow"><span className="live-dot" /> Universal model gateway</div><h1>Providers & Models</h1><div className="subtitle">Connect hosted APIs, routing gateways or local models through one auditable runtime contract.</div></div><div className="head-summary"><strong>{providers.length}</strong><span>connections configured</span></div></div>
      {error ? <ErrorNote error={error} /> : null}

      <section className="provider-section">
        <div className="section-heading"><div><span className="section-kicker">ACTIVE RUNTIME</span><h2>Connected providers</h2></div></div>
        {providers.length ? <div className="provider-connected-grid">{providers.map((provider) => <div className="card provider-connection" key={provider.uuid}>
          <div className="provider-connection-head"><span className="provider-logo"><Icon name="provider" /></span><span className={`badge ${provider.is_active ? "ok" : "muted"}`}>{provider.is_active ? "active" : "disabled"}</span></div>
          <strong>{provider.name}</strong><span className="provider-adapter">{provider.adapter_label || provider.adapter}</span>
          <div className="provider-endpoint mono">{provider.base_url || "Managed cloud endpoint"}</div>
          <div className="provider-metrics"><span><b>{provider.model_count}</b> models</span><span><b>{provider.credential_count}</b> credentials</span></div>
          {notices[provider.uuid] ? <div className="provider-notice">{notices[provider.uuid]}</div> : null}
          <div className="provider-actions">{provider.adapter !== "fake" ? <button className="btn" onClick={() => configure(provider)}>Configure</button> : null}<button className="btn" onClick={() => verify(provider)}>Test connection</button>{(discovered[provider.uuid]?.length || 0) > 0 ? <button className="btn primary" onClick={() => importModels(provider)}>Import models</button> : null}</div>
        </div>)}</div> : <div className="card directory-empty"><Icon name="provider" /><strong>No external provider connected</strong><span>Choose one from the catalogue below. The offline Fake provider remains available.</span></div>}
      </section>

      <section className="provider-section">
        <div className="section-heading"><div><span className="section-kicker">CATALOGUE</span><h2>{catalog.length} API and local integrations</h2></div></div>
        <div className="directory-toolbar card"><div className="directory-search"><Icon name="command" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search OpenAI, voice, image, local…" /></div><select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">All capabilities</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></div>
        <div className="provider-catalog-grid">{filtered.map((entry) => <button className="card provider-catalog-card" key={entry.key} onClick={() => { setEditing(undefined); setSelected(entry); }}>
          <div className="provider-catalog-top"><span className="provider-index">{String(entry.index).padStart(3, "0")}</span><span className={`provider-kind ${entry.local ? "local" : ""}`}>{entry.local ? "LOCAL" : entry.category.toUpperCase()}</span></div>
          <strong>{entry.name}</strong><span className="provider-capabilities">{entry.capabilities.join(" · ")}</span><span className="provider-transport">{entry.adapter.replaceAll("_", " ")} <Icon name="arrow" /></span>
        </button>)}</div>
      </section>

      {selected ? <Modal title={editing ? `Configure ${editing.name}` : `Connect ${selected.name}`} onClose={() => { setSelected(null); setEditing(undefined); }} wide><ConnectProviderForm entry={selected} existing={editing} onCancel={() => { setSelected(null); setEditing(undefined); }} onDone={async () => { setSelected(null); setEditing(undefined); await reloadProviders(); }} /></Modal> : null}
    </div>
  );
}
