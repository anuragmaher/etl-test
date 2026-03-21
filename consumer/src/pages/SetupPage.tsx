import { useState } from "react";
import Layout from "../components/Layout";
import GooglePickerButton from "../components/GooglePickerButton";
import PineconeConfigForm from "../components/PineconeConfigForm";
import { api } from "../api";
import { useNavigate } from "react-router-dom";

interface Folder {
  id: string;
  name: string;
}

export default function SetupPage() {
  const [selectedFolders, setSelectedFolders] = useState<Folder[]>([]);
  const [folderMessage, setFolderMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const handleSaveFolders = async () => {
    setSaving(true);
    setFolderMessage(null);
    try {
      await api.saveFolders(selectedFolders.map((f) => f.id));
      setFolderMessage({ type: "success", text: `Saved ${selectedFolders.length} folder(s)!` });
    } catch (err: any) {
      setFolderMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <div className="card">
        <h2>1. Select Google Drive Folders</h2>
        <p style={{ color: "#666", marginBottom: 16, fontSize: 14 }}>
          Choose which folders to sync documents from.
        </p>

        <GooglePickerButton
          selectedFolders={selectedFolders}
          onFoldersSelected={setSelectedFolders}
        />

        {selectedFolders.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <button className="btn btn-primary" onClick={handleSaveFolders} disabled={saving}>
              {saving ? "Saving..." : "Save Folder Selection"}
            </button>
          </div>
        )}

        {folderMessage && (
          <div className={`message ${folderMessage.type}`} style={{ marginTop: 12 }}>
            {folderMessage.text}
          </div>
        )}
      </div>

      <div className="card">
        <h2>2. Configure Pinecone</h2>
        <p style={{ color: "#666", marginBottom: 16, fontSize: 14 }}>
          Enter your Pinecone and OpenAI credentials for vector storage.
        </p>
        <PineconeConfigForm />
      </div>

      <div style={{ textAlign: "center", marginTop: 16 }}>
        <button className="btn btn-primary" onClick={() => navigate("/dashboard")} style={{ padding: "12px 32px" }}>
          Go to Dashboard
        </button>
      </div>
    </Layout>
  );
}
