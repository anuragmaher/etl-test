import { useState } from "react";
import { api } from "../api";

export default function PineconeConfigForm() {
  const [apiKey, setApiKey] = useState("");
  const [indexName, setIndexName] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.savePinecone({
        api_key: apiKey,
        index_name: indexName,
        openai_api_key: openaiKey,
      });
      setMessage({ type: "success", text: "Pinecone configuration saved!" });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      {message && <div className={`message ${message.type}`}>{message.text}</div>}

      <div className="form-group">
        <label>Pinecone API Key</label>
        <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="pc-..." />
      </div>

      <div className="form-group">
        <label>Index Name</label>
        <input value={indexName} onChange={(e) => setIndexName(e.target.value)} placeholder="my-index" />
      </div>

      <div className="form-group">
        <label>OpenAI API Key</label>
        <input type="password" value={openaiKey} onChange={(e) => setOpenaiKey(e.target.value)} placeholder="sk-..." />
      </div>

      <button className="btn btn-primary" onClick={handleSave} disabled={saving || !apiKey || !indexName || !openaiKey}>
        {saving ? "Saving..." : "Save Pinecone Config"}
      </button>
    </div>
  );
}
