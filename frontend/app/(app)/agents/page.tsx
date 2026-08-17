"use client";

import { useEffect, useState } from "react";
import { listCredentials, listModels, listUnits, searchAgents } from "@/lib/api";
import type { Agent, Credential, ModelInfo, OrgUnit } from "@/lib/types";
import Modal from "@/components/Modal";
import AgentEditor from "@/components/AgentEditor";
import StatusBadge from "@/components/StatusBadge";
import { Loading, ErrorNote } from "@/components/Feedback";
import Icon from "@/components/Icon";
import AgentCreateForm from "@/components/AgentCreateForm";

const PAGE_SIZE = 24;

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [units, setUnits] = useState<OrgUnit[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [unit, setUnit] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [editing, setEditing] = useState<Agent | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([listModels(controller.signal), listCredentials(controller.signal), listUnits(controller.signal)])
      .then(([modelRows, credentialRows, unitRows]) => {
        setModels(modelRows);
        setCredentials(credentialRows);
        setUnits(unitRows.filter((item) => item.kind === "department"));
      })
      .catch((err) => { if ((err as Error).name !== "AbortError") setError(err); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      searchAgents({ search, unit, status: statusFilter, page, pageSize: PAGE_SIZE }, controller.signal)
        .then((result) => { setAgents(result.results); setTotal(result.count); })
        .catch((err) => { if ((err as Error).name !== "AbortError") setError(err); })
        .finally(() => setLoading(false));
    }, 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [search, unit, statusFilter, page]);

  function onSaved(updated: Agent) {
    setAgents((previous) => previous.map((agent) => agent.uuid === updated.uuid ? updated : agent));
    setEditing(updated);
  }

  function resetAndSet(setter: (value: string) => void, value: string) {
    setPage(1);
    setter(value);
  }

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow"><span className="live-dot" /> Role-backed workforce</div>
          <h1>AI Workforce</h1>
          <div className="subtitle">One editable agent for every unique role imported from both company taxonomies.</div>
        </div>
        <div className="flex gap items-center"><div className="head-summary"><strong>{total.toLocaleString()}</strong><span>matching agents</span></div><button className="btn primary" onClick={() => setCreating(true)}>+ New agent</button></div>
      </div>

      {error ? <ErrorNote error={error} /> : null}

      <div className="directory-toolbar card">
        <div className="directory-search"><Icon name="command" /><input value={search} onChange={(event) => resetAndSet(setSearch, event.target.value)} placeholder="Search role, agent or responsibility…" /></div>
        <select value={unit} onChange={(event) => resetAndSet(setUnit, event.target.value)} aria-label="Filter by category">
          <option value="">All categories</option>
          {units.map((item) => <option key={item.uuid} value={item.uuid}>{item.name}</option>)}
        </select>
        <select value={statusFilter} onChange={(event) => resetAndSet(setStatusFilter, event.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option><option value="active">Active</option><option value="draft">Draft</option><option value="paused">Paused</option><option value="disabled">Disabled</option>
        </select>
      </div>

      {loading ? <Loading label="Loading workforce…" /> : agents.length ? (
        <div className="grid cols-3">
          {agents.map((agent) => (
            <button key={agent.uuid} className="card agent-card" style={{ textAlign: "left", cursor: "pointer" }} onClick={() => setEditing(agent)}>
              <div className="agent-card-head"><span className="agent-avatar"><Icon name="spark" /></span><StatusBadge status={agent.is_enabled ? agent.status : "disabled"} /></div>
              <strong className="agent-name">{agent.name}</strong>
              <div className="agent-role">{agent.role_name || "Specialist agent"}</div>
              <div className="muted agent-description">{agent.description || agent.role_name || "—"}</div>
              <div className="agent-card-footer">
                <div><small>Model</small><span>{agent.model_key || "Not assigned"}</span></div>
                <div><small>Provider</small><span>{agent.provider_name || agent.provider || "—"}</span></div>
                <span className="agent-open"><Icon name="arrow" /></span>
              </div>
            </button>
          ))}
        </div>
      ) : <div className="card directory-empty"><Icon name="agents" /><strong>No agents match these filters</strong><span>Change the search or category filter.</span></div>}

      <div className="directory-pagination">
        <span>Page {page.toLocaleString()} of {pages.toLocaleString()} · {total.toLocaleString()} agents</span>
        <div><button className="btn" disabled={page <= 1 || loading} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button><button className="btn" disabled={page >= pages || loading} onClick={() => setPage((value) => value + 1)}>Next</button></div>
      </div>

      {editing && <Modal title={<span>{editing.name} <span className="muted mono" style={{ fontSize: "0.8rem" }}>{editing.key}</span></span>} onClose={() => setEditing(null)} wide><AgentEditor agent={editing} models={models} credentials={credentials} onSaved={onSaved} /></Modal>}
      {creating && <Modal title="Create AI agent" onClose={() => setCreating(false)} wide><AgentCreateForm models={models} credentials={credentials} onCancel={() => setCreating(false)} onCreated={(agent) => { setAgents((current) => [agent, ...current]); setTotal((value) => value + 1); setCreating(false); setEditing(agent); }} /></Modal>}
    </div>
  );
}
