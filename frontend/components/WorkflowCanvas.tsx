"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  Position,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import type { WorkflowGraph } from "@/lib/types";

// A status map lets the control room tint nodes by their live NodeRun status
// (and show the current loop iteration). It's optional: /workflow renders the
// static graph with no statuses.
export interface NodeStatus {
  status: string; // running | succeeded | failed | passed | ...
  iteration?: number;
}
export type NodeStatusMap = Record<string, NodeStatus>;

interface WfNodeData {
  name: string;
  type: string;
  sub: string;
  status?: string;
  iteration?: number;
}

// Custom node renderer so we can style by workflow node type and overlay the
// live run status. Handles on both sides keep edges attaching cleanly.
function WfNode({ data }: NodeProps<WfNodeData>) {
  const statusClass = data.status ? `st-${data.status}` : "";
  return (
    <div className={`wf-node type-${data.type} ${statusClass}`}>
      <Handle type="target" position={Position.Left} />
      <div className="wf-name">{data.name}</div>
      {data.sub && <div className="wf-sub">{data.sub}</div>}
      {typeof data.iteration === "number" && data.iteration > 0 && (
        <div className="wf-iter" style={{ color: "var(--purple)" }}>
          iter #{data.iteration}
        </div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const NODE_TYPES = { wf: WfNode };

// Edge color hints: fail/give_up branches are the loop's "escape hatches".
function edgeColor(label: string): string {
  const l = label.toLowerCase();
  if (l === "fail") return "#f87171";
  if (l === "give_up") return "#fbbf24";
  if (l === "pass") return "#34d399";
  return "#4b5b70";
}

export default function WorkflowCanvas({
  graph,
  statusMap,
  height = 460,
}: {
  graph: WorkflowGraph;
  statusMap?: NodeStatusMap;
  height?: number;
}) {
  const nodes: Node<WfNodeData>[] = useMemo(() => {
    return graph.nodes.map((n) => {
      const sub = n.agent_key || n.role_key || n.type;
      const st = statusMap?.[n.key];
      return {
        id: n.key,
        type: "wf",
        position: { x: n.position_x ?? 0, y: n.position_y ?? 0 },
        data: {
          name: n.name || n.key,
          type: n.type,
          sub,
          status: st?.status,
          iteration: st?.iteration,
        },
      };
    });
  }, [graph.nodes, statusMap]);

  const edges: Edge[] = useMemo(() => {
    return graph.edges.map((e, i) => {
      // The loop-back edge (fail branch returning to an upstream node) is the
      // heart of the demo — draw it animated and curved so it reads as a cycle.
      const isLoopBack = e.label.toLowerCase() === "fail";
      const color = edgeColor(e.label);
      return {
        id: e.uuid || `${e.source_key}-${e.target_key}-${i}`,
        source: e.source_key,
        target: e.target_key,
        label: e.label || undefined,
        title: e.condition || undefined,
        animated: isLoopBack,
        type: "smoothstep",
        labelStyle: { fill: color, fontWeight: 600, fontSize: 11 },
        labelBgStyle: { fill: "#0b0e14", fillOpacity: 0.85 },
        style: {
          stroke: color,
          strokeWidth: isLoopBack ? 2.5 : 1.5,
          strokeDasharray: e.label.toLowerCase() === "give_up" ? "5 4" : undefined,
        },
        markerEnd: { type: MarkerType.ArrowClosed, color },
      };
    });
  }, [graph.edges]);

  return (
    <div className="canvas-wrap" style={{ height }}>
      <div className="canvas-hint">
        <span className="live-dot" /> Workflow map
        <small>Drag to explore · Scroll to zoom</small>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.12, minZoom: 0.48, maxZoom: 0.9 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.48}
        maxZoom={1.5}
      >
        <Background color="#26303f" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
