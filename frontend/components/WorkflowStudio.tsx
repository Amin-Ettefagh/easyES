"use client";

import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  saveWorkflowGraph,
  createArena,
  createWorkflowLink,
  testWorkflow,
  validateWorkflowGraph,
  type SaveWorkflowGraphInput,
} from "@/lib/api";
import type { Actor, Agent, Arena, ExecutionDetail, Project, Workflow, WorkflowGraph } from "@/lib/types";
import StatusBadge from "./StatusBadge";

type StudioNodeData = {
  name: string;
  nodeType: string;
  agentKey: string;
  arenaUuid: string;
  config: Record<string, unknown>;
};

const LIBRARY = [
  { group: "Triggers", items: [
    { type: "start", name: "Start", icon: "▶", tone: "mint" },
    { type: "event", name: "Event trigger", icon: "⚡", tone: "amber" },
  ]},
  { group: "Work", items: [
    { type: "agent_task", name: "AI agent", icon: "AI", tone: "violet" },
    { type: "task", name: "Task", icon: "✓", tone: "blue" },
    { type: "human_task", name: "Human task", icon: "H", tone: "rose" },
    { type: "tool", name: "Tool", icon: "⌘", tone: "slate" },
    { type: "review", name: "Review", icon: "◎", tone: "blue" },
    { type: "evaluation", name: "Evaluation", icon: "★", tone: "amber" },
  ]},
  { group: "Flow", items: [
    { type: "condition", name: "Condition", icon: "?", tone: "amber" },
    { type: "decision", name: "Decision", icon: "◇", tone: "amber" },
    { type: "parallel", name: "Parallel", icon: "⑂", tone: "violet" },
    { type: "join", name: "Merge", icon: "⋈", tone: "violet" },
    { type: "loop", name: "Loop", icon: "↻", tone: "rose" },
    { type: "wait", name: "Wait", icon: "◷", tone: "slate" },
    { type: "approval", name: "Approval", icon: "✓", tone: "mint" },
  ]},
  { group: "Finish", items: [
    { type: "end", name: "Complete", icon: "■", tone: "mint" },
    { type: "archive", name: "Archive", icon: "▣", tone: "rose" },
  ]},
];

const LIBRARY_MAP = new Map(LIBRARY.flatMap((group) => group.items).map((item) => [item.type, item]));

function StudioNode({ data, selected }: NodeProps<StudioNodeData>) {
  const meta = LIBRARY_MAP.get(data.nodeType) ?? { icon: "•", tone: "slate", name: data.nodeType };
  return (
    <div className={`studio-node tone-${meta.tone} ${selected ? "selected" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <span className="studio-node-icon">{meta.icon}</span>
      <span className="studio-node-copy"><strong>{data.name}</strong><small>{data.agentKey || meta.name}</small></span>
      <span className="studio-node-menu">•••</span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { studio: StudioNode };

function toCanvasNodes(graph: WorkflowGraph): Node<StudioNodeData>[] {
  return graph.nodes.map((node) => ({
    id: node.key,
    type: "studio",
    position: { x: node.position_x, y: node.position_y },
    data: { name: node.name, nodeType: node.type, agentKey: node.agent_key || "", arenaUuid: node.arena_uuid || "", config: node.config || {} },
  }));
}

function toCanvasEdges(graph: WorkflowGraph): Edge[] {
  return graph.edges.map((edge, index) => ({
    id: edge.uuid || `edge-${index}`,
    source: edge.source_key,
    target: edge.target_key,
    label: edge.label || undefined,
    type: "smoothstep",
    data: { condition: edge.condition || "", order: edge.order },
    markerEnd: { type: MarkerType.ArrowClosed },
  }));
}

export default function WorkflowStudio({
  graph,
  workflows,
  workspaces,
  workspaceUuid,
  agents,
  actors,
  onSelectWorkflow,
  onSelectWorkspace,
  onCreateWorkflow,
  onSaved,
}: {
  graph: WorkflowGraph;
  workflows: Workflow[];
  workspaces: Project[];
  workspaceUuid: string;
  agents: Agent[];
  actors: Actor[];
  onSelectWorkflow: (uuid: string) => void;
  onSelectWorkspace: (uuid: string) => void;
  onCreateWorkflow: () => void;
  onSaved: (graph: WorkflowGraph) => void;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<StudioNodeData>(toCanvasNodes(graph));
  const [edges, setEdges, onEdgesChange] = useEdgesState(toCanvasEdges(graph));
  const [instance, setInstance] = useState<ReactFlowInstance | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [mobilePanel, setMobilePanel] = useState<"palette" | "inspector" | null>(null);
  const [name, setName] = useState(graph.name);
  const [description, setDescription] = useState(graph.description);
  const [status, setStatus] = useState(graph.status);
  const [search, setSearch] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<"save" | "validate" | "test" | null>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "warn" | "err"; title: string; lines?: string[] } | null>(null);
  const [testRun, setTestRun] = useState<ExecutionDetail | null>(null);
  const [arenas, setArenas] = useState<Arena[]>(graph.arenas || []);
  const [arenaName, setArenaName] = useState("");
  const [linkTarget, setLinkTarget] = useState("");
  const [linkKind, setLinkKind] = useState<"related" | "depends_on" | "triggers" | "subworkflow">("related");

  useEffect(() => {
    setNodes(toCanvasNodes(graph));
    setEdges(toCanvasEdges(graph));
    setName(graph.name);
    setDescription(graph.description);
    setStatus(graph.status);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setMobilePanel(null);
    setDirty(false);
    setNotice(null);
    setTestRun(null);
    setArenas(graph.arenas || []);
  }, [graph, setEdges, setNodes]);

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId) ?? null;
  const filteredLibrary = useMemo(() => LIBRARY.map((group) => ({
    ...group,
    items: group.items.filter((item) => item.name.toLowerCase().includes(search.toLowerCase())),
  })).filter((group) => group.items.length), [search]);

  function markDirty() { setDirty(true); setNotice(null); }

  function addNodeOfType(nodeType: string, position?: { x: number; y: number }) {
    const meta = LIBRARY_MAP.get(nodeType)!;
    const base = nodeType.replace(/[^a-z0-9]+/g, "_");
    let key = base;
    let counter = 2;
    while (nodes.some((node) => node.id === key)) key = `${base}_${counter++}`;
    const fallback = instance?.project({ x: 480, y: 320 }) ?? { x: 260 + nodes.length * 28, y: 180 + (nodes.length % 4) * 90 };
    setNodes((current) => [...current, {
      id: key,
      type: "studio",
      position: position ?? fallback,
      data: {
        name: nodeType === "agent_task" ? "AI Agent" : meta.name,
        nodeType,
        agentKey: "",
        arenaUuid: "",
        config: nodeType === "agent_task" ? { stage: key, max_retries: 0 } : nodeType === "loop" ? { loop: true, max_iterations: 5 } : {},
      },
    }]);
    setSelectedNodeId(key);
    setSelectedEdgeId(null);
    setMobilePanel("inspector");
    markDirty();
  }

  function onDrop(event: React.DragEvent) {
    event.preventDefault();
    const nodeType = event.dataTransfer.getData("application/easyes-node");
    if (!nodeType || !instance) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    addNodeOfType(nodeType, instance.project({ x: event.clientX - bounds.left, y: event.clientY - bounds.top }));
  }

  function connect(connection: Connection) {
    setEdges((current) => addEdge({
      ...connection,
      id: `edge-${Date.now()}`,
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed },
      data: { condition: "", order: current.length },
    }, current));
    markDirty();
  }

  function updateSelectedNode(patch: Partial<StudioNodeData>) {
    if (!selectedNodeId) return;
    setNodes((current) => current.map((node) => node.id === selectedNodeId ? { ...node, data: { ...node.data, ...patch } } : node));
    markDirty();
  }

  function updateSelectedEdge(patch: { label?: string; condition?: string }) {
    if (!selectedEdgeId) return;
    setEdges((current) => current.map((edge) => edge.id === selectedEdgeId ? {
      ...edge,
      label: patch.label === undefined ? edge.label : patch.label || undefined,
      data: { ...edge.data, condition: patch.condition === undefined ? edge.data?.condition : patch.condition },
    } : edge));
    markDirty();
  }

  function removeSelection() {
    if (selectedNodeId) {
      setNodes((current) => current.filter((node) => node.id !== selectedNodeId));
      setEdges((current) => current.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId));
      setSelectedNodeId(null);
    } else if (selectedEdgeId) {
      setEdges((current) => current.filter((edge) => edge.id !== selectedEdgeId));
      setSelectedEdgeId(null);
    }
    markDirty();
  }

  function payload(): SaveWorkflowGraphInput {
    return {
      name,
      description,
      status,
      config: graph.config || {},
      nodes: nodes.map((node) => ({
        key: node.id,
        name: node.data.name,
        type: node.data.nodeType,
        agent_key: node.data.agentKey || undefined,
        arena_uuid: node.data.arenaUuid || null,
        config: node.data.config || {},
        position_x: Math.round(node.position.x),
        position_y: Math.round(node.position.y),
      })),
      edges: edges.map((edge, index) => ({
        source_key: edge.source,
        target_key: edge.target,
        label: String(edge.label || ""),
        condition: String(edge.data?.condition || ""),
        order: index,
      })),
    };
  }

  async function save() {
    setBusy("save");
    setNotice(null);
    try {
      const saved = await saveWorkflowGraph(graph.uuid, payload());
      onSaved(saved);
      setDirty(false);
      setNotice({ tone: "ok", title: "Workflow saved" });
      return saved;
    } catch (error) {
      showApiError(error, "Could not save workflow");
      return null;
    } finally { setBusy(null); }
  }

  async function validate() {
    setBusy("validate");
    setNotice(null);
    try {
      const result = await validateWorkflowGraph(graph.uuid, payload());
      setNotice({ tone: result.warnings.length ? "warn" : "ok", title: result.warnings.length ? "Valid with warnings" : "Workflow is valid", lines: result.warnings });
    } catch (error) { showApiError(error, "Validation failed"); }
    finally { setBusy(null); }
  }

  async function runTest() {
    setBusy("test");
    setNotice(null);
    setTestRun(null);
    try {
      const saved = dirty ? await saveWorkflowGraph(graph.uuid, payload()) : graph;
      if (dirty) { onSaved(saved); setDirty(false); }
      const result = await testWorkflow(graph.uuid, "success");
      setTestRun(result.execution);
      setNotice({ tone: result.execution.status === "succeeded" ? "ok" : "err", title: `Test ${result.execution.status}`, lines: result.execution.error ? [result.execution.error] : result.warnings });
    } catch (error) { showApiError(error, "Test run failed"); }
    finally { setBusy(null); }
  }

  function showApiError(error: unknown, fallback: string) {
    const body = typeof error === "object" && error && "body" in error ? (error as { body?: { errors?: string[]; warnings?: string[] } }).body : undefined;
    setNotice({ tone: "err", title: error instanceof Error ? error.message : fallback, lines: [...(body?.errors || []), ...(body?.warnings || [])] });
  }

  async function addArena() {
    if (!arenaName.trim() || !graph.workspace) return;
    setBusy("save");
    try {
      const colors = ["#9b5f34", "#4f7a68", "#5b668f", "#8a5969"];
      const arena = await createArena({ workspace: graph.workspace, workflow: graph.uuid, name: arenaName.trim(), color: colors[arenas.length % colors.length] });
      setArenas((current) => [...current, arena]);
      setArenaName("");
      setNotice({ tone: "ok", title: `Arena “${arena.name}” created` });
    } catch (error) { showApiError(error, "Could not create arena"); }
    finally { setBusy(null); }
  }

  async function addWorkflowRelation() {
    if (!graph.workspace || !linkTarget) return;
    setBusy("save"); setNotice(null);
    try { await createWorkflowLink({ workspace: graph.workspace, source: graph.uuid, target: linkTarget, kind: linkKind }); setLinkTarget(""); setNotice({ tone: "ok", title: "Workflow relation saved" }); }
    catch (error) { showApiError(error, "Could not link workflows"); }
    finally { setBusy(null); }
  }

  return (
    <div className="workflow-studio">
      <header className="studio-header">
        <div className="studio-workflow-select"><span className="studio-app-icon">⌁</span><span className="studio-context-selects"><select aria-label="Workspace" value={workspaceUuid} onChange={(e) => onSelectWorkspace(e.target.value)}><option value="">Company workflow library</option>{workspaces.map((workspace) => <option key={workspace.uuid} value={workspace.uuid}>{workspace.name}</option>)}</select><select aria-label="Workflow" value={graph.uuid} onChange={(e) => onSelectWorkflow(e.target.value)}>{workflows.map((workflow) => <option key={workflow.uuid} value={workflow.uuid}>{workflow.name}</option>)}</select></span><button className="studio-icon-button" onClick={onCreateWorkflow} title="New workflow">＋</button></div>
        <div className="studio-save-state"><span className={dirty ? "dirty-dot" : "saved-dot"} />{dirty ? "Unsaved changes" : "All changes saved"}</div>
        <div className="studio-actions"><button className="btn studio-mobile-tool" onClick={() => setMobilePanel(mobilePanel === "palette" ? null : "palette")} aria-expanded={mobilePanel === "palette"}>＋ Steps</button><button className="btn studio-mobile-tool" onClick={() => setMobilePanel(mobilePanel === "inspector" ? null : "inspector")} aria-expanded={mobilePanel === "inspector"}>⚙ Setup</button><button className="btn compact studio-validate" onClick={validate} disabled={!!busy}>{busy === "validate" ? "Checking…" : "Validate"}</button><button className="btn test-button" onClick={runTest} disabled={!!busy}><span>▶</span>{busy === "test" ? "Running…" : "Test workflow"}</button><button className="btn primary compact" onClick={save} disabled={!!busy || !dirty}>{busy === "save" ? "Saving…" : "Save"}</button></div>
      </header>
      {notice && <div className={`studio-notice ${notice.tone}`}><strong>{notice.title}</strong>{notice.lines?.map((line) => <span key={line}>{line}</span>)}<button onClick={() => setNotice(null)}>×</button></div>}
      <div className="studio-body">
        {mobilePanel && <button className="studio-drawer-scrim" onClick={() => setMobilePanel(null)} aria-label="Close workflow panel" />}
        <aside className={`node-palette ${mobilePanel === "palette" ? "mobile-open" : ""}`}>
          <div className="palette-head"><span><strong>Add a step</strong><small>Drag onto the canvas</small></span><button className="studio-drawer-close" onClick={() => setMobilePanel(null)} aria-label="Close node library">×</button></div>
          <div className="palette-search"><span>⌕</span><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search nodes…" /></div>
          <div className="arena-builder"><label>Team arenas</label><div>{arenas.map((arena) => <span key={arena.uuid}><i style={{ background: arena.color }} />{arena.name}</span>)}</div><div className="arena-create"><input value={arenaName} onChange={(e) => setArenaName(e.target.value)} placeholder="e.g. AI team" disabled={!graph.workspace} /><button onClick={addArena} disabled={!arenaName.trim() || !graph.workspace}>＋</button></div>{!graph.workspace ? <small>Assign this workflow to a workspace first.</small> : null}</div>
          <div className="palette-scroll">{filteredLibrary.map((group) => <section key={group.group}><h4>{group.group}</h4>{group.items.map((item) => <button key={item.type} draggable onDragStart={(e) => { e.dataTransfer.setData("application/easyes-node", item.type); e.dataTransfer.effectAllowed = "move"; }} onClick={() => addNodeOfType(item.type)}><span className={`palette-icon tone-${item.tone}`}>{item.icon}</span><span>{item.name}<small>{item.type.replace(/_/g, " ")}</small></span><i>⠿</i></button>)}</section>)}</div>
        </aside>
        <main className="studio-canvas" onDrop={onDrop} onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }}>
          {nodes.length === 0 && <div className="canvas-empty"><span>＋</span><strong>Add your first step</strong><small>Drag a trigger from the node panel</small></div>}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={(changes) => { onNodesChange(changes); if (changes.some((change) => change.type === "position" && change.dragging === false)) markDirty(); }}
            onEdgesChange={(changes) => { onEdgesChange(changes); if (changes.some((change) => change.type === "remove")) markDirty(); }}
            onConnect={connect}
            onInit={setInstance}
            onNodeClick={(_, node) => { setSelectedNodeId(node.id); setSelectedEdgeId(null); setMobilePanel("inspector"); }}
            onEdgeClick={(_, edge) => { setSelectedEdgeId(edge.id); setSelectedNodeId(null); setMobilePanel("inspector"); }}
            onPaneClick={() => { setSelectedNodeId(null); setSelectedEdgeId(null); }}
            fitView
            fitViewOptions={{ padding: 0.15, minZoom: 0.52, maxZoom: 0.9 }}
            minZoom={0.25}
            maxZoom={1.7}
            defaultEdgeOptions={{ type: "smoothstep", markerEnd: { type: MarkerType.ArrowClosed } }}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={22} size={1} />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable nodeStrokeWidth={3} />
          </ReactFlow>
          <div className="studio-canvas-badge"><span>{nodes.length} nodes</span><span>{edges.length} connections</span></div>
        </main>
        <aside className={`node-inspector ${mobilePanel === "inspector" ? "mobile-open" : ""}`}>
          <button className="studio-drawer-close inspector-drawer-close" onClick={() => setMobilePanel(null)} aria-label="Close inspector">×</button>
          {selectedNode ? <NodeInspector node={selectedNode} agents={agents} actors={actors} arenas={arenas} onChange={updateSelectedNode} onDelete={removeSelection} /> : selectedEdge ? <EdgeInspector edge={selectedEdge} onChange={updateSelectedEdge} onDelete={removeSelection} /> : <WorkflowInspector name={name} description={description} status={status} onName={(value) => { setName(value); markDirty(); }} onDescription={(value) => { setDescription(value); markDirty(); }} onStatus={(value) => { setStatus(value); markDirty(); }} />}
          {!selectedNode && !selectedEdge && graph.workspace ? <div className="workflow-relations"><strong>Related workflows</strong><small>Model dependencies or trigger chains inside this workspace.</small><select value={linkKind} onChange={(e) => setLinkKind(e.target.value as typeof linkKind)}><option value="related">Related</option><option value="depends_on">Depends on</option><option value="triggers">Triggers</option><option value="subworkflow">Subworkflow</option></select><select value={linkTarget} onChange={(e) => setLinkTarget(e.target.value)}><option value="">Select workflow…</option>{workflows.filter((workflow) => workflow.uuid !== graph.uuid).map((workflow) => <option key={workflow.uuid} value={workflow.uuid}>{workflow.name}</option>)}</select><button className="btn" onClick={addWorkflowRelation} disabled={!linkTarget || !!busy}>Link workflow</button></div> : null}
          {testRun && <div className="test-result-card"><div><span className="test-result-icon">✓</span><span><strong>Last test</strong><small>{testRun.node_runs.length} nodes executed</small></span></div><StatusBadge status={testRun.status} /><dl><div><dt>Tokens</dt><dd>{testRun.total_input_tokens + testRun.total_output_tokens}</dd></div><div><dt>Cost</dt><dd>${Number(testRun.total_cost).toFixed(4)}</dd></div></dl></div>}
        </aside>
      </div>
    </div>
  );
}

function WorkflowInspector({ name, description, status, onName, onDescription, onStatus }: { name: string; description: string; status: string; onName: (value: string) => void; onDescription: (value: string) => void; onStatus: (value: string) => void }) {
  return <div className="inspector-content"><div className="inspector-head"><span className="inspector-type-icon">⌁</span><div><strong>Workflow settings</strong><small>Definition and publishing</small></div></div><div className="field"><label>Name</label><input value={name} onChange={(e) => onName(e.target.value)} /></div><div className="field"><label>Description</label><textarea rows={4} value={description} onChange={(e) => onDescription(e.target.value)} /></div><div className="field"><label>Status</label><select value={status} onChange={(e) => onStatus(e.target.value)}><option value="draft">Draft</option><option value="published">Published</option><option value="archived">Archived</option></select></div><div className="inspector-tip"><strong>How it works</strong><p>Add nodes from the left, connect their handles, then configure each step here. Save before using this workflow in a project.</p></div></div>;
}

function NodeInspector({ node, agents, actors, arenas, onChange, onDelete }: { node: Node<StudioNodeData>; agents: Agent[]; actors: Actor[]; arenas: Arena[]; onChange: (patch: Partial<StudioNodeData>) => void; onDelete: () => void }) {
  const cfg = node.data.config || {};
  const isLoop = ["loop", "condition", "decision"].includes(node.data.nodeType);
  function config(key: string, value: unknown) { onChange({ config: { ...cfg, [key]: value } }); }
  const humans = actors.filter((actor) => actor.kind === "human" || actor.kind === "hybrid");
  return <div className="inspector-content"><div className="inspector-head"><span className={`inspector-type-icon tone-${LIBRARY_MAP.get(node.data.nodeType)?.tone || "slate"}`}>{LIBRARY_MAP.get(node.data.nodeType)?.icon || "•"}</span><div><strong>{LIBRARY_MAP.get(node.data.nodeType)?.name || node.data.nodeType}</strong><small>{node.id}</small></div><button className="inspector-close" onClick={onDelete} title="Delete node">⌫</button></div><div className="field"><label>Display name</label><input value={node.data.name} onChange={(e) => onChange({ name: e.target.value })} /></div><div className="field"><label>Arena / team</label><select value={node.data.arenaUuid} onChange={(e) => onChange({ arenaUuid: e.target.value })}><option value="">No arena</option>{arenas.map((arena) => <option key={arena.uuid} value={arena.uuid}>{arena.name}</option>)}</select></div><div className="field"><label>Node type</label><select value={node.data.nodeType} onChange={(e) => onChange({ nodeType: e.target.value })}>{LIBRARY.flatMap((group) => group.items).map((item) => <option key={item.type} value={item.type}>{item.name}</option>)}</select></div>{["agent_task", "task", "review", "evaluation"].includes(node.data.nodeType) && <><div className="field"><label>Assigned agent</label><select value={node.data.agentKey} onChange={(e) => onChange({ agentKey: e.target.value })}><option value="">Deterministic / unassigned</option>{agents.map((agent) => <option key={agent.uuid} value={agent.key}>{agent.name}</option>)}</select></div><div className="field"><label>Execution stage</label><input className="mono" value={String(cfg.stage || node.id)} onChange={(e) => config("stage", e.target.value)} /></div><div className="field"><label>Automatic retries</label><input type="number" min={0} max={10} value={Number(cfg.max_retries || 0)} onChange={(e) => config("max_retries", Number(e.target.value))} /></div></>}{["human_task", "approval"].includes(node.data.nodeType) && <><div className="field"><label>{node.data.nodeType === "human_task" ? "Assigned human assistant" : "Approver"}</label><select value={String(cfg.actor_uuid || "")} onChange={(e) => config("actor_uuid", e.target.value)}><option value="">Any operator</option>{humans.map((actor) => <option key={actor.uuid} value={actor.uuid}>{actor.name}</option>)}</select></div><div className="field"><label>Instruction shown at the gate</label><textarea rows={4} value={String(cfg.prompt || "")} onChange={(e) => config("prompt", e.target.value)} placeholder="Describe what must be reviewed or delivered…" /></div>{node.data.nodeType === "human_task" ? <div className="field"><label>Acceptance criteria</label><textarea rows={3} value={String(cfg.acceptance_criteria || "")} onChange={(e) => config("acceptance_criteria", e.target.value)} /></div> : <label className="toggle-row"><span><strong>Auto approve</strong><small>Keep disabled to require an operator decision.</small></span><input type="checkbox" checked={Boolean(cfg.auto_approve)} onChange={(e) => config("auto_approve", e.target.checked)} /></label>}</>}{isLoop && <><label className="toggle-row"><span><strong>Loop controller</strong><small>Route failures back for another pass</small></span><input type="checkbox" checked={Boolean(cfg.loop)} onChange={(e) => config("loop", e.target.checked)} /></label>{Boolean(cfg.loop) && <div className="row"><div className="field"><label>Max iterations</label><input type="number" min={1} value={Number(cfg.max_iterations || 5)} onChange={(e) => config("max_iterations", Number(e.target.value))} /></div><div className="field"><label>Failure label</label><input value={String(cfg.loop_back_label || "fail")} onChange={(e) => config("loop_back_label", e.target.value)} /></div></div>}</>}<button className="danger-link" onClick={onDelete}>Delete this node</button></div>;
}

function EdgeInspector({ edge, onChange, onDelete }: { edge: Edge; onChange: (patch: { label?: string; condition?: string }) => void; onDelete: () => void }) {
  return <div className="inspector-content"><div className="inspector-head"><span className="inspector-type-icon tone-blue">→</span><div><strong>Connection</strong><small>{edge.source} → {edge.target}</small></div><button className="inspector-close" onClick={onDelete}>⌫</button></div><div className="field"><label>Branch label</label><input value={String(edge.label || "")} onChange={(e) => onChange({ label: e.target.value })} placeholder="pass, fail, give_up…" /></div><div className="field"><label>Condition</label><textarea className="mono" rows={5} value={String(edge.data?.condition || "")} onChange={(e) => onChange({ condition: e.target.value })} placeholder="evaluation.passed == True" /><div className="hint">Leave empty for an unconditional connection.</div></div><button className="danger-link" onClick={onDelete}>Delete connection</button></div>;
}
