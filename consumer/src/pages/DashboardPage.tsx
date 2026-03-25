import { useEffect, useState, useRef } from "react";
import Layout from "../components/Layout";
import DocumentList from "../components/DocumentList";
import SyncStatusBadge from "../components/SyncStatusBadge";
import AskPanel from "../components/AskPanel";
import { api } from "../api";

export default function DashboardPage() {
  const [status, setStatus] = useState({ status: "idle", last_run: null, docs_synced: 0, docs_skipped: 0, error: null as string | null, warnings: [] as string[] });
  const [documents, setDocuments] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<number | null>(null);

  const loadData = async () => {
    try {
      const [statusRes, docsRes] = await Promise.all([
        api.syncStatus(),
        api.listDocuments(),
      ]);
      setStatus(statusRes);
      setDocuments(docsRes);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadData();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setError("");
    try {
      await api.triggerSync();

      pollRef.current = window.setInterval(async () => {
        const res = await api.syncStatus();
        setStatus(res);
        if (res.status === "idle") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setSyncing(false);
          const docsRes = await api.listDocuments();
          setDocuments(docsRes);
        }
      }, 2000);
    } catch (err: any) {
      setError(err.message);
      setSyncing(false);
    }
  };

  return (
    <Layout wide>
      <div className="dashboard-layout">
        <div className="dashboard-main">
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>Sync Status</h2>
              <button className="btn btn-primary" onClick={handleSync} disabled={syncing}>
                {syncing ? "Syncing..." : "Sync Now"}
              </button>
            </div>

            <SyncStatusBadge
              status={status.status}
              lastRun={status.last_run}
              docsSynced={status.docs_synced}
              docsSkipped={status.docs_skipped}
              error={status.error}
              warnings={status.warnings}
            />

            {error && <div className="message error" style={{ marginTop: 12 }}>{error}</div>}
          </div>

          <div className="card">
            <h2>Synced Documents</h2>
            <DocumentList documents={documents} />
          </div>
        </div>

        <div className="dashboard-aside">
          <AskPanel />
        </div>
      </div>
    </Layout>
  );
}
