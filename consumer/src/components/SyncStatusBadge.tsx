interface Props {
  status: string;
  lastRun?: string | null;
  docsSynced: number;
  docsSkipped: number;
}

export default function SyncStatusBadge({ status, lastRun, docsSynced, docsSkipped }: Props) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <span className={`status-badge ${status}`}>{status}</span>
      {lastRun && (
        <span style={{ fontSize: 13, color: "#666" }}>
          Last run: {new Date(lastRun).toLocaleString()} — {docsSynced} synced, {docsSkipped} skipped
        </span>
      )}
    </div>
  );
}
