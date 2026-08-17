"use client";

import { useCallback, useEffect, useState } from "react";
import { createWorkflow, getWorkflow, listActors, listAgents, listProjects, listWorkflows, saveWorkflowGraph } from "@/lib/api";
import type { Actor, Agent, Project, Workflow, WorkflowGraph } from "@/lib/types";
import WorkflowStudio from "@/components/WorkflowStudio";
import Modal from "@/components/Modal";
import { ErrorNote, Loading } from "@/components/Feedback";

export default function WorkflowPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [graph, setGraph] = useState<WorkflowGraph | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actors, setActors] = useState<Actor[]>([]);
  const [workspaces, setWorkspaces] = useState<Project[]>([]);
  const [workspaceUuid, setWorkspaceUuid] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [creating, setCreating] = useState(false);

  const openWorkflow = useCallback(async (uuid: string) => {
    setError(null);
    try { setGraph(await getWorkflow(uuid)); }
    catch (err) { setError(err); }
  }, []);

  useEffect(() => {
    Promise.all([listWorkflows(), listAgents(), listProjects(), listActors()])
      .then(async ([available, workforce, spaces, companyActors]) => {
        setWorkflows(available);
        setAgents(workforce);
        setActors(companyActors);
        setWorkspaces(spaces);
        const primary = available.find((item) => item.key === "software_delivery") ?? available[0];
        if (primary) { setWorkspaceUuid(primary.workspace || spaces[0]?.uuid || ""); setGraph(await getWorkflow(primary.uuid)); }
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Opening workflow studio…" />;
  if (error && !graph) return <ErrorNote error={error} />;

  const visibleWorkflows = workflows.filter((workflow) => workspaceUuid ? workflow.workspace === workspaceUuid : workflow.workspace === null);

  async function selectWorkspace(uuid: string) {
    setWorkspaceUuid(uuid);
    const next = workflows.find((workflow) => uuid ? workflow.workspace === uuid : workflow.workspace === null);
    if (next) await openWorkflow(next.uuid); else setGraph(null);
  }

  return (
    <div className="workflow-page-full">
      {error ? <ErrorNote error={error} /> : null}
      {graph ? (
        <WorkflowStudio
          graph={graph}
          workflows={visibleWorkflows}
          workspaces={workspaces}
          workspaceUuid={workspaceUuid}
          agents={agents}
          actors={actors}
          onSelectWorkflow={openWorkflow}
          onSelectWorkspace={selectWorkspace}
          onCreateWorkflow={() => setCreating(true)}
          onSaved={(saved) => {
            setGraph(saved);
            setWorkflows((current) => current.map((item) => item.uuid === saved.uuid ? { ...item, ...saved } : item));
          }}
        />
      ) : (
        <div className="studio-first-workflow"><span>⌁</span><h1>Build your first workflow</h1><p>{workspaces.length ? "Connect agents, decisions and quality gates inside the selected workspace." : "Create a workspace from Dashboard first, then add its workflows."}</p><button className="btn primary big" onClick={() => setCreating(true)} disabled={!workspaces.length}>Create workflow</button></div>
      )}
      {creating && <NewWorkflowModal workspaces={workspaces} workspaceUuid={workspaceUuid || workspaces[0]?.uuid || ""} onClose={() => setCreating(false)} onCreated={(created, saved) => { setWorkspaceUuid(created.workspace || ""); setWorkflows((current) => [created, ...current]); setGraph(saved); setCreating(false); }} />}
    </div>
  );
}

function NewWorkflowModal({ workspaces, workspaceUuid, onClose, onCreated }: { workspaces: Project[]; workspaceUuid: string; onClose: () => void; onCreated: (workflow: Workflow, graph: WorkflowGraph) => void }) {
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [workspace, setWorkspace] = useState(workspaceUuid);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const workflow = await createWorkflow({ name: name.trim(), key: key.trim() || undefined, description: description.trim(), workspace });
      const graph = await saveWorkflowGraph(workflow.uuid, {
        name: workflow.name,
        description: workflow.description,
        status: "draft",
        config: {},
        nodes: [{ key: "start", name: "Start", type: "start", config: {}, position_x: 120, position_y: 220 }],
        edges: [],
      });
      onCreated(workflow, graph);
    } catch (err) { setError(err); }
    finally { setBusy(false); }
  }

  return <Modal title="Create workflow" onClose={onClose}><form onSubmit={submit}>{error ? <ErrorNote error={error} /> : null}<div className="field"><label>Workspace</label><select value={workspace} onChange={(e) => setWorkspace(e.target.value)} required>{workspaces.map((item) => <option key={item.uuid} value={item.uuid}>{item.name}</option>)}</select></div><div className="field"><label>Workflow name</label><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Product discovery" required autoFocus /></div><div className="field"><label>Key</label><input className="mono" value={key} onChange={(e) => setKey(e.target.value)} placeholder="generated-from-name" /></div><div className="field"><label>Description</label><textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What outcome does this workflow produce?" /></div><div className="modal-actions"><button className="btn" type="button" onClick={onClose}>Cancel</button><button className="btn primary" type="submit" disabled={busy || !workspace}>{busy ? "Creating…" : "Create and open"}</button></div></form></Modal>;
}
