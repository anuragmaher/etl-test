import { useEffect, useState } from "react";
import { api } from "../api";

interface NotionItem {
  id: string;
  title: string;
  type: string;
  icon: string;
  last_edited: string;
  url: string;
}

export default function NotionSetup() {
  const [token, setToken] = useState("");
  const [connected, setConnected] = useState(false);
  const [items, setItems] = useState<NotionItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Check if already connected on mount
  useEffect(() => {
    api.notionStatus().then((res) => {
      if (res.configured) {
        setConnected(true);
        // Load pages
        api.listNotionPages().then((pagesRes) => {
          setItems(pagesRes.items);
        }).catch(() => {});
      }
    }).catch(() => {});
  }, []);

  const handleConnect = async () => {
    setLoading(true);
    setMessage(null);
    try {
      await api.saveNotionToken(token);
      setConnected(true);
      await refreshPages();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const refreshPages = async () => {
    setLoading(true);
    try {
      const res = await api.listNotionPages();
      setItems(res.items);
      setMessage({ type: "success", text: `Found ${res.items.length} pages/databases.` });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const handleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((i) => i.id)));
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setMessage(null);
    try {
      await api.saveNotionPages(Array.from(selectedIds));
      setMessage({ type: "success", text: `Saved ${selectedIds.size} Notion item(s) for sync!` });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {message && <div className={`message ${message.type}`}>{message.text}</div>}

      {!connected && (
        <>
          <div className="form-group">
            <label>Notion Integration Token</label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="ntn_..."
            />
          </div>
          <p style={{ fontSize: 12, color: "#999", marginBottom: 12 }}>
            Create an integration at notion.so/my-integrations, then share pages with it.
          </p>
          <button className="btn btn-primary" onClick={handleConnect} disabled={loading || !token}>
            {loading ? "Connecting..." : "Connect Notion"}
          </button>
        </>
      )}

      {connected && (
        <div style={{ marginBottom: 12 }}>
          <button
            className="btn btn-secondary"
            onClick={() => { setConnected(false); setItems([]); setSelectedIds(new Set()); setToken(""); setMessage(null); }}
            style={{ fontSize: 13 }}
          >
            Change Token / Reconnect
          </button>
          {items.length === 0 && (
            <p style={{ marginTop: 12, color: "#999", fontSize: 14 }}>
              No pages found. Share pages with your integration in Notion first, then refresh.
            </p>
          )}
          {items.length > 0 && (
            <button className="btn btn-secondary" onClick={refreshPages} disabled={loading} style={{ marginLeft: 8, fontSize: 13 }}>
              {loading ? "Refreshing..." : "Refresh Pages"}
            </button>
          )}
        </div>
      )}

      {connected && items.length > 0 && (
        <div className="file-tree">
          <div className="tree-toolbar">
            <label>
              <input
                type="checkbox"
                checked={selectedIds.size === items.length && items.length > 0}
                onChange={handleSelectAll}
              />
              <strong>Select All</strong> ({items.length} items)
            </label>
            <span className="tree-selected-count">{selectedIds.size} selected</span>
          </div>
          <div className="tree-list">
            {items.map((item) => (
              <div key={item.id} className="tree-item">
                <span className="tree-toggle" style={{ visibility: "hidden" }}>▸</span>
                <input
                  type="checkbox"
                  checked={selectedIds.has(item.id)}
                  onChange={() => handleToggle(item.id)}
                />
                <span className="tree-icon">
                  {item.icon || (item.type === "database" ? "📊" : "📄")}
                </span>
                <span className="tree-name">{item.title}</span>
                <span className="tree-count">{item.type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {connected && selectedIds.size > 0 && (
        <div style={{ marginTop: 16 }}>
          <button className="btn btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? "Saving..." : `Save Selection (${selectedIds.size} items)`}
          </button>
        </div>
      )}
    </div>
  );
}
