"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getProject,
  getWorkflow,
  getExecution,
  listExecutions,
  listWorkflows,
  startExecution,
  listArtifacts,
  listEvaluations,
  getArtifact,
  createTask,
  listActors,
  pauseExecution,
  resolveIntervention,
  updateTask,
  getWorkspaceRepository,
  getWorkspaceRevision,
} from "@/lib/api";
import type {
  ProjectDetail,
  WorkflowGraph,
  ExecutionDetail,
  Execution,
  Artifact,
  ArtifactDetail,
  Evaluation,
  Scenario,
  Actor,
  Intervention,
  Task,
  WorkspaceRepository,
} from "@/lib/types";
import WorkflowCanvas, { type NodeStatusMap } from "@/components/WorkflowCanvas";
import EventLog from "@/components/EventLog";
import StatusBadge from "@/components/StatusBadge";
import Modal from "@/components/Modal";
import { Loading, ErrorNote } from "@/components/Feedback";

const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);
const SCENARIOS: { value: Scenario; label: string }[] = [
  { value: "success", label: "Success (passes first try)" },
  { value: "fail_once", label: "Fail once (loops then passes)" },
  { value: "always_fail", label: "Always fail (gives up at max)" },
];

type Tab = "artifacts" | "evaluations" | "tasks" | "repository";

export default function ControlRoomPage() {
  const params = useParams<{ uuid: string }>();
  const projectUuid = params.uuid;

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [graph, setGraph] = useState<WorkflowGraph | null>(null);
  const [execution, setExecution] = useState<ExecutionDetail | null>(null);
  const [scenario, setScenario] = useState<Scenario>("fail_once");
  const [selectedWorkflow, setSelectedWorkflow] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [starting, setStarting] = useState(false);
  const [operatorPrompt, setOperatorPrompt] = useState("");
  const [gateBusy, setGateBusy] = useState(false);
  const [actors, setActors] = useState<Actor[]>([]);

  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [tab, setTab] = useState<Tab>("evaluations");
  const [openArtifact, setOpenArtifact] = useState<ArtifactDetail | null>(null);
  const [repository, setRepository] = useState<WorkspaceRepository | null>(null);
  const [revisionDiff, setRevisionDiff] = useState("");

  const pollRef = useRef<ReturnType<typeof setTimeout>>();

  const isRunning = execution ? !TERMINAL.has(execution.status) : false;

  // Initial load: project, its workflow graph, and the latest execution (if any).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const proj = await getProject(projectUuid);
        if (cancelled) return;
        setProject(proj);
        setSelectedWorkflow(proj.workflows?.find((item) => item.key === proj.workflow_key)?.uuid || proj.workflows?.[0]?.uuid || "");
        if (proj.workflow_key) setScenario((proj.context?.scenario as Scenario) || "fail_once");

        // Load the workflow graph by matching the project's workflow_key.
        const [graphDetail, execs, companyActors] = await Promise.all([
          loadGraphForProject(proj),
          listExecutions(),
          listActors(),
        ]);
        if (cancelled) return;
        if (graphDetail) setGraph(graphDetail);
        setActors(companyActors);

        const latest = execs.find((e) => e.project_key === proj.key);
        if (latest) {
          const detail = await getExecution(latest.uuid);
          if (!cancelled) setExecution(detail);
        }
        await refreshSideData(proj.uuid, cancelled);
      } catch (e) {
        if (!cancelled) setError(e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectUuid]);

  async function loadGraphForProject(
    proj: ProjectDetail
  ): Promise<WorkflowGraph | null> {
    // The project's workflow FK is a numeric id; the graph endpoint is keyed by
    // uuid. Resolve via the workflow list matching the workflow_key.
    const wfs = await listWorkflows();
    const wf =
      wfs.find((w) => w.key === proj.workflow_key) ??
      wfs.find((w) => w.id === proj.workflow) ??
      wfs[0];
    if (!wf) return null;
    return getWorkflow(wf.uuid);
  }

  const refreshSideData = useCallback(
    async (uuid: string, cancelled = false) => {
      try {
        const [arts, evals, repo] = await Promise.all([
          listArtifacts(uuid),
          listEvaluations(uuid),
          getWorkspaceRepository(uuid),
        ]);
        if (!cancelled) {
          setArtifacts(arts);
          setEvaluations(evals);
          setRepository(repo);
        }
      } catch {
        /* non-fatal */
      }
    },
    []
  );

  // While an execution is running (thread backend), poll its detail so the
  // canvas node statuses + loop panel update live. Stop when terminal.
  useEffect(() => {
    if (!execution || !isRunning) return;
    let cancelled = false;

    async function tick() {
      try {
        const detail = await getExecution(execution!.uuid);
        if (cancelled) return;
        setExecution(detail);
        if (TERMINAL.has(detail.status)) {
          // Final refresh of artifacts/evals + project status.
          if (project) await refreshSideData(project.uuid);
          const proj = await getProject(projectUuid);
          if (!cancelled) setProject(proj);
          return;
        }
      } catch {
        /* keep polling */
      }
      if (!cancelled) pollRef.current = setTimeout(tick, 1500);
    }

    pollRef.current = setTimeout(tick, 1500);
    return () => {
      cancelled = true;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [execution?.uuid, isRunning]);

  async function onStart() {
    if (!project) return;
    setStarting(true);
    setError(null);
    try {
      const detail = await startExecution(project.uuid, scenario, selectedWorkflow || undefined);
      setExecution(detail);
      // Kick side-data + project refresh; polling effect takes over from here.
      await refreshSideData(project.uuid);
    } catch (e) {
      setError(e);
    } finally {
      setStarting(false);
    }
  }

  async function onPause() {
    if (!execution) return;
    setGateBusy(true); setError(null);
    try { await pauseExecution(execution.uuid, operatorPrompt.trim() || "Operator found an issue and paused the run for review."); setExecution(await getExecution(execution.uuid)); setOperatorPrompt(""); }
    catch (e) { setError(e); }
    finally { setGateBusy(false); }
  }

  async function onResolveGate(gate: Intervention, decision: "approve" | "reject", response: string) {
    if (!execution) return;
    setGateBusy(true); setError(null);
    try { await resolveIntervention(gate.uuid, decision, response); setExecution(await getExecution(execution.uuid)); setProject(await getProject(projectUuid)); }
    catch (e) { setError(e); }
    finally { setGateBusy(false); }
  }

  if (loading) return <Loading label="Loading control room…" />;
  if (!project) return <ErrorNote error={error ?? "Project not found."} />;

  // Build a node-key -> live status map from the current execution's node runs.
  // Later runs of the same node (loop iterations) win, so the canvas shows the
  // most recent state and the highest iteration.
  const statusMap: NodeStatusMap = {};
  if (execution) {
    for (const nr of execution.node_runs) {
      const prev = statusMap[nr.node_key];
      if (!prev || nr.iteration >= (prev.iteration ?? 0)) {
        statusMap[nr.node_key] = { status: nr.status, iteration: nr.iteration };
      }
    }
  }

  const loop = execution?.loop_states?.[0];

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="muted mono" style={{ fontSize: "0.75rem" }}>
            <Link href="/dashboard">← Dashboard</Link> · {project.key}
          </div>
          <h1 style={{ marginTop: "0.35rem" }}>{project.name}</h1>
          <div className="subtitle">{project.idea || "—"}</div>
        </div>
        <StatusBadge status={project.status} />
      </div>

      {error ? <ErrorNote error={error} /> : null}

      {/* Run controls */}
      <div className="card mb">
        <div className="flex between items-center gap" style={{ flexWrap: "wrap" }}>
          <div className="row" style={{ margin: 0, flex: 1 }}><div className="field" style={{ margin: 0, minWidth: 220 }}><label>Workflow</label><select value={selectedWorkflow} onChange={async (e) => { setSelectedWorkflow(e.target.value); if (e.target.value) setGraph(await getWorkflow(e.target.value)); }} disabled={isRunning}>{project.workflows?.map((workflow) => <option key={workflow.uuid} value={workflow.uuid}>{workflow.name}</option>)}</select></div><div className="field" style={{ margin: 0, minWidth: 280 }}>
            <label>Scenario</label>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value as Scenario)}
              disabled={isRunning}
            >
              {SCENARIOS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div></div>
          <button
            className="btn primary big"
            onClick={onStart}
            disabled={starting || isRunning || !selectedWorkflow}
          >
            {isRunning ? "Running…" : starting ? "Starting…" : "▶ Start Run"}
          </button>
        </div>
        {execution && execution.status === "running" ? <div className="operator-stop-row"><input value={operatorPrompt} onChange={(e) => setOperatorPrompt(e.target.value)} placeholder="Describe the issue before pausing…" /><button className="btn" onClick={onPause} disabled={gateBusy}>■ Pause &amp; ask operator</button></div> : null}
        {!selectedWorkflow && (
          <div className="hint" style={{ color: "var(--warn)", marginTop: "0.5rem" }}>
            This workspace has no workflow attached, so it cannot be run.
          </div>
        )}
      </div>

      {/* Outcome banner */}
      {execution && (
        <RunBanner execution={execution} />
      )}
      {execution?.interventions?.filter((item) => item.status === "pending").map((gate) => <GateCard key={gate.uuid} gate={gate} busy={gateBusy} onResolve={onResolveGate} />)}

      <div className="control-grid">
        {/* Left: the live graph + loop panel */}
        <div>
          {graph ? (
            <WorkflowCanvas graph={graph} statusMap={statusMap} height={460} />
          ) : (
            <div className="card">No workflow graph available.</div>
          )}

          {loop && (
            <div className="card loop-panel mt">
              <h3>QA Loop</h3>
              <div className="flex between">
                <span className="muted">
                  Iteration {loop.iteration} / {loop.max_iterations}
                </span>
                <span className="muted">
                  {loop.consecutive_failures} consecutive failures
                </span>
              </div>
              <div className="bar">
                <span
                  style={{
                    width: `${Math.min(
                      100,
                      (loop.iteration / Math.max(1, loop.max_iterations)) * 100
                    )}%`,
                  }}
                />
              </div>
              <div className="flex gap" style={{ flexWrap: "wrap", marginTop: "0.5rem" }}>
                <span className="chip">
                  {loop.is_active ? "active" : "stopped"}
                </span>
                {loop.stop_reason && <span className="chip">stop: {loop.stop_reason}</span>}
                <span className="chip">threshold {loop.failure_threshold}</span>
                <span className="chip">max cost {String(loop.max_cost)}</span>
              </div>
            </div>
          )}

          {execution && (
            <div className="card mt">
              <h3>Run metrics</h3>
              <div className="stat-row">
                <div className="stat">
                  <span className="value">{execution.total_input_tokens}</span>
                  <span className="label">Input tokens</span>
                </div>
                <div className="stat">
                  <span className="value">{execution.total_output_tokens}</span>
                  <span className="label">Output tokens</span>
                </div>
                <div className="stat">
                  <span className="value">
                    ${Number(execution.total_cost).toFixed(4)}
                  </span>
                  <span className="label">Cost</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: the live event log */}
        <div>
          <div className="flex between items-center mb">
            <h3 style={{ margin: 0 }}>Live events</h3>
            {execution && <StatusBadge status={execution.status} />}
          </div>
          <EventLog
            executionUuid={execution?.uuid ?? null}
            active={isRunning}
          />
        </div>
      </div>

      {/* Tabs: artifacts / evaluations / tasks */}
      <div className="tabs">
        <button
          className={`tab ${tab === "evaluations" ? "active" : ""}`}
          onClick={() => setTab("evaluations")}
        >
          Evaluations ({evaluations.length})
        </button>
        <button
          className={`tab ${tab === "artifacts" ? "active" : ""}`}
          onClick={() => setTab("artifacts")}
        >
          Artifacts ({artifacts.length})
        </button>
        <button
          className={`tab ${tab === "tasks" ? "active" : ""}`}
          onClick={() => setTab("tasks")}
        >
          Tasks ({project.tasks.length})
        </button>
        <button className={`tab ${tab === "repository" ? "active" : ""}`} onClick={() => setTab("repository")}>Git history ({repository?.commits.length || 0})</button>
      </div>

      {tab === "evaluations" && (
        <div className="card">
          {evaluations.length === 0 ? (
            <div className="muted">No evaluations yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Iter</th>
                  <th>Verdict</th>
                  <th>Tests</th>
                  <th>Coverage</th>
                  <th>Score</th>
                  <th>Feedback</th>
                </tr>
              </thead>
              <tbody>
                {[...evaluations]
                  .sort((a, b) => a.iteration - b.iteration)
                  .map((ev) => (
                    <tr key={ev.uuid}>
                      <td className="mono">{ev.iteration}</td>
                      <td>
                        <StatusBadge
                          status={ev.passed ? "passed" : "failed"}
                          label={ev.verdict || (ev.passed ? "pass" : "fail")}
                        />
                      </td>
                      <td className="mono">
                        {ev.tests_total - ev.tests_failed}/{ev.tests_total}
                      </td>
                      <td className="mono">
                        {fmtPct(ev.requirement_coverage)} /{" "}
                        {fmtPct(ev.coverage_threshold)}
                      </td>
                      <td className="mono">{fmtNum(ev.score)}</td>
                      <td className="muted" style={{ maxWidth: 360 }}>
                        {ev.feedback || ev.summary || "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "artifacts" && (
        <div className="card">
          {artifacts.length === 0 ? (
            <div className="muted">No artifacts produced yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Kind</th>
                  <th>Iter</th>
                  <th>Node</th>
                  <th>By</th>
                </tr>
              </thead>
              <tbody>
                {artifacts.map((a) => (
                  <tr
                    key={a.uuid}
                    style={{ cursor: "pointer" }}
                    onClick={async () => {
                      try {
                        setOpenArtifact(await getArtifact(a.uuid));
                      } catch (e) {
                        setError(e);
                      }
                    }}
                  >
                    <td style={{ color: "var(--accent)" }}>{a.name}</td>
                    <td>
                      <span className="chip">{a.kind}</span>
                    </td>
                    <td className="mono">{a.iteration}</td>
                    <td className="mono muted">{a.node_key || "—"}</td>
                    <td className="muted">{a.produced_by_name || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "tasks" && (
        <TaskBoard projectUuid={project.uuid} tasks={project.tasks} actors={actors} onChanged={async () => setProject(await getProject(projectUuid))} />
      )}

      {tab === "repository" && <div className="repository-panel"><div className="card repository-sidebar"><div className="section-head"><div><span className="section-kicker">Internal repository</span><h3>{repository?.branch || "main"}</h3></div><span className={`badge ${repository?.dirty ? "warn" : "ok"}`}>{repository?.dirty ? "changes" : "clean"}</span></div>{repository?.commits.length ? repository.commits.map((commit) => <button key={commit.hash} onClick={async () => { try { setRevisionDiff((await getWorkspaceRevision(project.uuid, commit.hash)).diff); } catch (e) { setError(e); } }}><span className="mono">{commit.short_hash}</span><strong>{commit.message}</strong><small>{new Date(commit.date).toLocaleString()} · {commit.author}</small></button>) : <div className="muted">No commits yet. Agent artifacts will be committed automatically.</div>}</div><pre className="code repository-diff">{revisionDiff || "Select a commit to inspect its files and diff."}</pre></div>}

      {openArtifact && (
        <Modal
          title={openArtifact.name}
          onClose={() => setOpenArtifact(null)}
          wide
        >
          <div className="mb">
            <span className="chip">{openArtifact.kind}</span>
            <span className="chip">{openArtifact.content_type || "text"}</span>
            <span className="chip">iter {openArtifact.iteration}</span>
          </div>
          <pre className="code">{openArtifact.content}</pre>
        </Modal>
      )}
    </div>
  );
}

function GateCard({ gate, busy, onResolve }: { gate: Intervention; busy: boolean; onResolve: (gate: Intervention, decision: "approve" | "reject", response: string) => void }) {
  const [response, setResponse] = useState("");
  return <div className="gate-card"><div className="gate-icon">!</div><div className="gate-copy"><span className="section-kicker">{gate.kind.replace("_", " ")} · execution stopped</span><strong>{gate.prompt}</strong><small>{gate.assigned_actor_name ? `Assigned to ${gate.assigned_actor_name}` : "Waiting for an operator"}{gate.node_key ? ` · ${gate.node_key}` : ""}</small><textarea rows={3} value={response} onChange={(e) => setResponse(e.target.value)} placeholder={gate.kind === "human_task" ? "Describe the completed work and provide the result…" : "Decision note / operator instruction…"} /><div className="flex gap"><button className="btn primary" disabled={busy || (gate.kind === "human_task" && !response.trim())} onClick={() => onResolve(gate, "approve", response)}>{gate.kind === "human_task" ? "Complete task & continue" : "Approve & continue"}</button><button className="btn" disabled={busy} onClick={() => onResolve(gate, "reject", response)}>Reject run</button></div></div></div>;
}

const BOARD_COLUMNS = [
  { key: "pending", label: "Backlog" },
  { key: "in_progress", label: "In progress" },
  { key: "blocked", label: "Blocked" },
  { key: "done", label: "Done" },
];

function TaskBoard({ projectUuid, tasks, actors, onChanged }: { projectUuid: string; tasks: Task[]; actors: Actor[]; onChanged: () => Promise<void> }) {
  const [creating, setCreating] = useState(false); const [title, setTitle] = useState(""); const [priority, setPriority] = useState("medium"); const [actor, setActor] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  async function add(event: React.FormEvent) { event.preventDefault(); setBusy(true); setError(null); try { await createTask({ project: projectUuid, title: title.trim(), priority, assigned_actor: actor || null, status: "pending" }); setTitle(""); setCreating(false); await onChanged(); } catch (e) { setError(e); } finally { setBusy(false); } }
  async function move(task: Task, status: string) { setBusy(true); try { await updateTask(task.uuid, { status }); await onChanged(); } catch (e) { setError(e); } finally { setBusy(false); } }
  return <div className="task-board-wrap">{error ? <ErrorNote error={error} /> : null}<div className="flex between items-center mb"><div><span className="section-kicker">Workspace issues</span><h3>Task board</h3></div><button className="btn primary" onClick={() => setCreating(true)}>+ Task</button></div><div className="task-board">{BOARD_COLUMNS.map((column) => <section key={column.key}><header><strong>{column.label}</strong><span>{tasks.filter((task) => task.status === column.key).length}</span></header><div>{tasks.filter((task) => task.status === column.key).map((task) => <article key={task.uuid}><span className={`task-priority ${task.priority}`}>{task.priority || "medium"}</span><strong>{task.title}</strong><small>{task.assigned_actor_name || "Unassigned"} · {task.issue_type || task.kind}</small><select aria-label={`Move ${task.title}`} value={task.status} onChange={(e) => move(task, e.target.value)} disabled={busy}>{BOARD_COLUMNS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></article>)}</div></section>)}</div>{creating ? <Modal title="Create task" onClose={() => setCreating(false)}><form onSubmit={add}><div className="field"><label>Title</label><input value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus /></div><div className="row"><div className="field"><label>Priority</label><select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></div><div className="field"><label>Assignee</label><select value={actor} onChange={(e) => setActor(e.target.value)}><option value="">Unassigned</option>{actors.map((item) => <option key={item.uuid} value={item.uuid}>{item.name} · {item.kind}</option>)}</select></div></div><div className="modal-actions"><button className="btn" type="button" onClick={() => setCreating(false)}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? "Creating…" : "Create task"}</button></div></form></Modal> : null}</div>;
}

function RunBanner({ execution }: { execution: Execution }) {
  const status = execution.status.toLowerCase();
  if (status === "succeeded") {
    return (
      <div className="banner ok">
        ✔ Run completed — {execution.stop_reason || "pass"}
      </div>
    );
  }
  if (status === "failed") {
    return (
      <div className="banner err">
        ✖ Run failed / archived — {execution.stop_reason || execution.error || "error"}
      </div>
    );
  }
  if (status === "cancelled") {
    return <div className="banner err">Run cancelled.</div>;
  }
  if (status === "waiting_for_approval" || status === "paused") {
    return <div className="banner warn">■ Execution is stopped and waiting for a human/operator decision.</div>;
  }
  return (
    <div className="banner run">
      <span className="spinner" style={{ width: 16, height: 16 }} /> Run in progress —{" "}
      {execution.status}…
    </div>
  );
}

function fmtPct(v: number | string): string {
  const n = typeof v === "string" ? parseFloat(v) : v;
  if (Number.isNaN(n)) return "—";
  // Coverage may be stored as 0..1 or 0..100; normalise to a percent display.
  const pct = n <= 1 ? n * 100 : n;
  return `${pct.toFixed(0)}%`;
}

function fmtNum(v: number | string): string {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return Number.isNaN(n) ? "—" : n.toFixed(1);
}
