interface Props {
  status: string;
  lastRun?: string | null;
  docsSynced: number;
  docsSkipped: number;
  error?: string | null;
  warnings?: string[];
}

export default function SyncStatusBadge({ status, lastRun, docsSynced, docsSkipped, error, warnings }: Props) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <span className={`status-badge ${status}`}>{status}</span>
        {lastRun && (
          <span style={{ fontSize: 13, color: "#666" }}>
            Last run: {new Date(lastRun).toLocaleString()} — {docsSynced} synced, {docsSkipped} skipped
          </span>
        )}
      </div>

      {error && (
        <div className="message error" style={{ marginTop: 12 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {warnings && warnings.length > 0 && (
        <div style={{ marginTop: 12 }}>
          {warnings.map((w, i) => (
            <div key={i} className="message" style={{ background: "#fff3e0", color: "#e65100" }}>
              <strong>Warning:</strong> {w}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
