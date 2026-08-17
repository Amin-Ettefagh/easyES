import type { ReactNode } from "react";

// Maps backend status strings to a badge style + label. Covers execution,
// project, node-run and evaluation states with sensible fallbacks.
type Tone = "ok" | "err" | "warn" | "info" | "muted" | "run";

const TONE: Record<string, Tone> = {
  // good
  succeeded: "ok",
  completed: "ok",
  passed: "ok",
  active: "ok",
  published: "ok",
  // bad
  failed: "err",
  cancelled: "err",
  rejected: "err",
  archived: "err",
  // in-flight
  running: "run",
  queued: "run",
  pending: "warn",
  waiting: "warn",
  waiting_for_approval: "warn",
  paused: "warn",
  // neutral
  draft: "muted",
  disabled: "muted",
};

export default function StatusBadge({
  status,
  label,
}: {
  status: string;
  label?: ReactNode;
}) {
  const key = (status || "").toLowerCase();
  const tone = TONE[key] ?? "muted";
  return (
    <span className={`badge ${tone}`}>
      <span className="dot" />
      {label ?? status.replace(/_/g, " ")}
    </span>
  );
}
