"use client";

import { useEffect, useState } from "react";
import { createActor, createOrganization, listActors, listOrganizations, listProjects, listRoles, listUnits, me } from "@/lib/api";
import type { Actor, Organization, OrgUnit, Project, Role } from "@/lib/types";
import { Loading, ErrorNote } from "@/components/Feedback";
import Modal from "@/components/Modal";
import { saveUser, setActiveOrganization } from "@/lib/auth";

export default function CompanyPage() {
  const [units, setUnits] = useState<OrgUnit[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [actors, setActors] = useState<Actor[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [workspaces, setWorkspaces] = useState<Project[]>([]);
  const [creatingCompany, setCreatingCompany] = useState(false);
  const [creatingHuman, setCreatingHuman] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    Promise.all([listUnits(), listRoles(), listActors(), listOrganizations(), listProjects()])
      .then(([u, r, a, companies, spaces]) => {
        setUnits(u);
        setRoles(r);
        setActors(a);
        setOrganizations(companies);
        setWorkspaces(spaces);
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading company structure…" />;

  const humans = actors.filter((a) => a.kind === "human" || a.kind === "hybrid");
  const agents = actors.filter((a) => a.kind === "ai_agent");
  const systems = actors.filter((a) => a.kind === "system");

  // Group roles by their unit for display.
  const rolesByUnit = new Map<string, Role[]>();
  for (const r of roles) {
    const key = r.unit_name || "Unassigned";
    if (!rolesByUnit.has(key)) rolesByUnit.set(key, []);
    rolesByUnit.get(key)!.push(r);
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow"><span className="live-dot" /> Human + AI organization</div>
          <h1>Company structure</h1>
          <div className="subtitle">
            See how departments, responsibilities and intelligent actors connect.
          </div>
        </div>
        <div className="flex gap items-center"><div className="head-summary"><strong>{actors.length}</strong><span>active actors</span></div><button className="btn" onClick={() => setCreatingHuman(true)}>+ Human assistant</button><button className="btn primary" onClick={() => setCreatingCompany(true)}>+ New company</button></div>
      </div>

      {error ? <ErrorNote error={error} /> : null}

      <div className="grid cols-2 mb"><div className="card company-panel"><div className="section-head"><div><span className="section-kicker">Tenancy</span><h3>Your companies</h3></div><span className="count-pill">{organizations.length}</span></div>{organizations.map((company) => <div className="company-summary-row" key={company.uuid}><span><strong>{company.name}</strong><small>{company.type.replaceAll("_", " ")}</small></span><span>{company.project_count} workspaces</span></div>)}</div><div className="card company-panel"><div className="section-head"><div><span className="section-kicker">Delivery</span><h3>Workspaces</h3></div><span className="count-pill">{workspaces.length}</span></div>{workspaces.length ? workspaces.map((workspace) => <div className="company-summary-row" key={workspace.uuid}><span><strong>{workspace.name}</strong><small>{workspace.idea || "Project workspace"}</small></span><span>{workspace.workflow_count || workspace.workflows?.length || 0} workflows</span></div>) : <div className="muted">Create a workspace from Overview.</div>}</div></div>

      <div className="grid cols-2">
        <div className="card company-panel">
          <div className="section-head"><div><span className="section-kicker">Structure</span><h3>Org units</h3></div><span className="count-pill">{units.length}</span></div>
          {units.length === 0 ? (
            <div className="muted">No units defined.</div>
          ) : (
            <ul className="list-tight">
              {units.map((u) => (
                <li key={u.uuid} className="flex between items-center">
                  <span>{u.name}</span>
                  <span className="chip">{u.kind}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card company-panel">
          <div className="section-head"><div><span className="section-kicker">Workforce</span><h3>Actors</h3></div><span className="count-pill">{actors.length}</span></div>
          <div className="mb muted" style={{ fontSize: "0.8rem" }}>
            {humans.length} human · {agents.length} AI · {systems.length} system
          </div>
          <ul className="list-tight">
            {actors.map((a) => (
              <li key={a.uuid} className="flex between items-center">
                <div>
                  <span style={{ fontWeight: 600 }}>{a.name}</span>{" "}
                  <span className="chip">{a.kind.replace("_", " ")}</span>
                  <div className="muted mono" style={{ fontSize: "0.72rem" }}>
                    {a.agent_key || a.username || "—"}
                    {a.role_assignments.length > 0 &&
                      " · " +
                        a.role_assignments
                          .map((ra) => ra.role_name)
                          .filter(Boolean)
                          .join(", ")}
                  </div>
                </div>
                <span
                  className={`badge ${
                    a.presence === "online" || a.presence === "available"
                      ? "ok"
                      : "muted"
                  }`}
                >
                  {a.presence || "—"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card mt">
        <h3>Roles</h3>
        {[...rolesByUnit.entries()].map(([unit, unitRoles]) => (
          <div key={unit} style={{ marginBottom: "1.25rem" }}>
            <div
              className="muted"
              style={{
                textTransform: "uppercase",
                fontSize: "0.72rem",
                letterSpacing: "0.05em",
                marginBottom: "0.5rem",
              }}
            >
              {unit}
            </div>
            <div className="grid cols-3">
              {unitRoles.map((r) => (
                <div
                  key={r.uuid}
                  style={{
                    border: "1px solid var(--border-soft)",
                    borderRadius: "var(--radius-sm)",
                    padding: "0.75rem",
                  }}
                >
                  <div style={{ fontWeight: 600 }}>{r.name}</div>
                  <div
                    className="muted"
                    style={{ fontSize: "0.8rem", margin: "0.25rem 0 0.5rem" }}
                  >
                    {r.description || "—"}
                  </div>
                  <div>
                    {r.capability_keys.length === 0 ? (
                      <span className="muted" style={{ fontSize: "0.72rem" }}>
                        no capabilities
                      </span>
                    ) : (
                      r.capability_keys.map((c) => (
                        <span key={c} className="chip">
                          {c}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {creatingCompany ? <NewCompanyModal onClose={() => setCreatingCompany(false)} onCreated={async (company) => { const user = await me(); saveUser(user); setActiveOrganization(company.uuid); window.location.reload(); }} /> : null}
      {creatingHuman ? <NewHumanModal roles={roles} onClose={() => setCreatingHuman(false)} onCreated={(actor) => { setActors((current) => [...current, actor]); setCreatingHuman(false); }} /> : null}
    </div>
  );
}

function NewHumanModal({ roles, onClose, onCreated }: { roles: Role[]; onClose: () => void; onCreated: (actor: Actor) => void }) {
  const [name, setName] = useState(""); const [kind, setKind] = useState<"human" | "hybrid">("human"); const [roleId, setRoleId] = useState<number | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  async function submit(event: React.FormEvent) { event.preventDefault(); setBusy(true); setError(null); try { onCreated(await createActor({ name: name.trim(), kind, role_ids: roleId ? [roleId] : [] })); } catch (e) { setError(e); setBusy(false); } }
  return <Modal title="Add human assistant" onClose={onClose}><form onSubmit={submit}>{error ? <ErrorNote error={error} /> : null}<div className="field"><label>Name</label><input value={name} onChange={(e) => setName(e.target.value)} required autoFocus /></div><div className="row"><div className="field"><label>Mode</label><select value={kind} onChange={(e) => setKind(e.target.value as "human" | "hybrid")}><option value="human">Human</option><option value="hybrid">Human + AI hybrid</option></select></div><div className="field"><label>Primary role</label><select value={roleId ?? ""} onChange={(e) => setRoleId(e.target.value ? Number(e.target.value) : null)}><option value="">No role</option>{roles.map((role) => <option key={role.uuid} value={role.id}>{role.name}</option>)}</select></div></div><div className="hint">This creates an assignable human actor. Link a login user later when inviting company members.</div><div className="modal-actions"><button className="btn" type="button" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? "Adding…" : "Add assistant"}</button></div></form></Modal>;
}

function NewCompanyModal({ onClose, onCreated }: { onClose: () => void; onCreated: (company: Organization) => void }) {
  const [name, setName] = useState(""); const [type, setType] = useState("software_company"); const [description, setDescription] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  async function submit(event: React.FormEvent) { event.preventDefault(); setBusy(true); setError(null); try { onCreated(await createOrganization({ name: name.trim(), type, description: description.trim() })); } catch (e) { setError(e); setBusy(false); } }
  return <Modal title="Create company" onClose={onClose}><form onSubmit={submit}>{error ? <ErrorNote error={error} /> : null}<div className="field"><label>Company name</label><input value={name} onChange={(e) => setName(e.target.value)} required autoFocus /></div><div className="field"><label>Company type</label><select value={type} onChange={(e) => setType(e.target.value)}><option value="software_company">Software company</option><option value="startup">Startup</option><option value="enterprise">Enterprise</option><option value="research_lab">Research lab</option><option value="agency">Agency</option><option value="other">Other</option></select></div><div className="field"><label>Description</label><textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} /></div><div className="modal-actions"><button className="btn" type="button" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? "Creating…" : "Create company"}</button></div></form></Modal>;
}
