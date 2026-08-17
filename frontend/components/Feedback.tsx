export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="center-note">
      <span className="spinner" />
      <div style={{ marginTop: "0.75rem" }}>{label}</div>
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const msg =
    error instanceof Error ? error.message : typeof error === "string" ? error : "Something went wrong.";
  return <div className="error-note">{msg}</div>;
}

export function Empty({ label }: { label: string }) {
  return <div className="center-note">{label}</div>;
}
