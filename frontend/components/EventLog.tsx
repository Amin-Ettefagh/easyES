"use client";

import { useEffect, useRef, useState } from "react";
import { listEvents } from "@/lib/api";
import type { EventItem } from "@/lib/types";

// Live event feed. Rather than an EventSource (which can't send the JWT auth
// header the API requires), we POLL GET /events/?execution=<uuid> every 1.5s and
// dedupe by the monotonic `seq`. Polling stops once `active` goes false (the
// parent flips this when the execution reaches a terminal state).
export default function EventLog({
  executionUuid,
  active,
}: {
  executionUuid: string | null;
  active: boolean;
}) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const seenSeq = useRef<Set<number>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastExec = useRef<string | null>(null);

  // Reset the buffer when we switch to a different execution.
  useEffect(() => {
    if (executionUuid !== lastExec.current) {
      lastExec.current = executionUuid;
      seenSeq.current = new Set();
      setEvents([]);
    }
  }, [executionUuid]);

  useEffect(() => {
    if (!executionUuid) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const rows = await listEvents(executionUuid as string);
        if (cancelled) return;
        const fresh = rows.filter((r) => !seenSeq.current.has(r.seq));
        if (fresh.length) {
          fresh.forEach((r) => seenSeq.current.add(r.seq));
          setEvents((prev) =>
            [...prev, ...fresh].sort((a, b) => a.seq - b.seq)
          );
        }
      } catch {
        // Transient errors are ignored; the next tick retries.
      } finally {
        // Keep polling while active; do one final catch-up poll after the run
        // ends so late-written events aren't missed.
        if (!cancelled && active) {
          timer = setTimeout(poll, 1500);
        }
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [executionUuid, active]);

  // Auto-scroll to the newest line.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events]);

  function levelClass(level: string): string {
    const l = (level || "").toLowerCase();
    if (l === "error" || l === "critical") return "level-error";
    if (l === "warning" || l === "warn") return "level-warning";
    if (l === "success") return "level-success";
    return "";
  }

  return (
    <div className="event-log" ref={scrollRef}>
      {events.length === 0 && (
        <div className="muted" style={{ padding: "0.5rem" }}>
          {executionUuid ? "Waiting for events…" : "Start a run to see live events."}
        </div>
      )}
      {events.map((e) => (
        <div key={e.seq} className={`event-line ${levelClass(e.level)}`}>
          <span className="seq">{e.seq}</span>
          <span className="etype">{e.type}</span>
          <span className="emsg">
            {e.node_key ? <span className="muted">[{e.node_key}] </span> : null}
            {e.message}
          </span>
        </div>
      ))}
    </div>
  );
}
