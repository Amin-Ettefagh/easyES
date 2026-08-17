"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  listOrganizations,
  listProjects,
  listExecutions,
  listWorkflows,
  createProject,
} from "@/lib/api";
import type { Organization, Project, Execution, Workflow } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import Modal from "@/components/Modal";
import { Loading, ErrorNote } from "@/components/Feedback";
import Icon from "@/components/Icon";

export default function DashboardPage() {
  const [org, setOrg] = useState<Organization | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [showNew, setShowNew] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [orgs, projs, execs] = await Promise.all([
        listOrganizations(),
        listProjects(),
        listExecutions(),
      ]);
      setOrg(orgs[0] ?? null);
      setProjects(projs);
      setExecutions(execs);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <Loading label="Loading company…" />;

  const runningCount = executions.filter((e) => ["running", "queued", "pending"].includes(e.status)).length;
  const completedCount = executions.filter((e) => e.status === "succeeded").length;

  return (
    <div>
      <div className="page-head dashboard-head">
        <div>
          <div className="eyebrow"><span className="live-dot" /> Operational overview</div>
          <h1>Good to see you, {org?.name ?? "amin"}.</h1>
          <div className="subtitle">
            Your company is online. Direct the workforce and follow delivery from one place.
          </div>
        </div>
        <button className="btn primary" onClick={() => setShowNew(true)}>
          <Icon name="project" /> New workspace
        </button>
      </div>

      {error ? <ErrorNote error={error} /> : null}

      {org && (
        <div className="stat-row dashboard-stats">
            <div className="stat">
              <span className="stat-icon violet"><Icon name="roles" /></span>
              <span className="value">{org.role_count}</span>
              <span className="label">Roles</span>
              <small>Across 6 departments</small>
            </div>
            <div className="stat">
              <span className="stat-icon mint"><Icon name="agents" /></span>
              <span className="value">{org.agent_count}</span>
              <span className="label">AI Agents</span>
              <small>All systems available</small>
            </div>
            <div className="stat">
              <span className="stat-icon blue"><Icon name="project" /></span>
              <span className="value">{org.project_count}</span>
              <span className="label">Workspaces</span>
              <small>{runningCount} currently active</small>
            </div>
            <div className="stat">
              <span className="stat-icon amber"><Icon name="activity" /></span>
              <span className="value">{executions.length}</span>
              <span className="label">Runs</span>
              <small>{completedCount} completed</small>
            </div>
        </div>
      )}

      <div className="grid dashboard-grid mt">
        <div className="card projects-panel">
          <div className="section-head"><div><span className="section-kicker">Portfolio</span><h3>Active workspaces</h3></div><span className="count-pill">{projects.length}</span></div>
          {projects.length === 0 ? (
            <div className="muted">No workspaces yet — create one, then design one or more workflows inside it.</div>
          ) : (
            <div className="project-list">
              {projects.map((p) => (
                <Link key={p.uuid} href={`/projects/${p.uuid}`} className="project-row">
                  <span className="project-icon"><Icon name="command" /></span>
                  <div className="project-row-main">
                    <strong>{p.name}</strong>
                    <span>{p.workflow_count || p.workflows?.length || 0} workflows · {p.execution_count} runs</span>
                  </div>
                  <StatusBadge status={p.status} />
                  <Icon name="arrow" className="row-arrow" />
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="card runs-panel">
          <div className="section-head"><div><span className="section-kicker">Live operations</span><h3>Recent runs</h3></div><span className="live-chip"><span className="live-dot" /> live</span></div>
          {executions.length === 0 ? (
            <div className="muted">No executions yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Scenario</th>
                  <th>Status</th>
                  <th>Stop reason</th>
                </tr>
              </thead>
              <tbody>
                {executions.slice(0, 12).map((e) => (
                  <tr key={e.uuid}>
                    <td className="mono">{e.project_key || "—"}</td>
                    <td>{e.scenario || "—"}</td>
                    <td>
                      <StatusBadge status={e.status} />
                    </td>
                    <td className="muted">{e.stop_reason || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showNew && (
        <NewProjectModal
          onClose={() => setShowNew(false)}
          onCreated={() => {
            setShowNew(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function NewProjectModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [idea, setIdea] = useState("");
  const [requirements, setRequirements] = useState("");
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [workflowId, setWorkflowId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // Load available workflows so the new project is runnable immediately.
  useEffect(() => {
    listWorkflows()
      .then((wfs) => {
        setWorkflows(wfs);
        const primary = wfs.find((w) => w.key === "software_delivery") ?? wfs[0];
        if (primary) setWorkflowId(primary.id);
      })
      .catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const reqs = requirements
        .split("\n")
        .map((r) => r.trim())
        .filter(Boolean);
      await createProject({
        name: name.trim(),
        key: key.trim() || name.trim().toLowerCase().replace(/\s+/g, "-"),
        idea: idea.trim(),
        requirements: reqs,
        workflow: workflowId,
      });
      onCreated();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="New Workspace" onClose={onClose}>
      <form onSubmit={submit}>
        {error ? <ErrorNote error={error} /> : null}
        <div className="row">
          <div className="field">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="field">
            <label>Key</label>
            <input
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="auto from name"
              className="mono"
            />
          </div>
        </div>
        <div className="field">
          <label>Initial workflow template (optional)</label>
          <select
            value={workflowId ?? ""}
            onChange={(e) =>
              setWorkflowId(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">— none —</option>
            {workflows.map((w) => (
              <option key={w.uuid} value={w.id}>
                {w.name} ({w.key})
              </option>
            ))}
          </select>
          <div className="hint">You can add multiple workflows later from Workflow Studio.</div>
        </div>
        <div className="field">
          <label>Idea</label>
          <textarea
            rows={3}
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Build a URL shortener with analytics…"
          />
        </div>
        <div className="field">
          <label>Requirements (one per line)</label>
          <textarea
            rows={4}
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
            placeholder={"Shorten URLs\nTrack click counts\nREST API"}
          />
        </div>
        <div className="flex gap">
          <button className="btn primary" type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create workspace"}
          </button>
          <button className="btn" type="button" onClick={onClose}>
            Cancel
          </button>
        </div>
      </form>
    </Modal>
  );
}
