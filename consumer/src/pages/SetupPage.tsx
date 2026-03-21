import { useState } from "react";
import Layout from "../components/Layout";
import GooglePickerButton from "../components/GooglePickerButton";
import NotionSetup from "../components/NotionSetup";
import PineconeConfigForm from "../components/PineconeConfigForm";
import { api } from "../api";
import { useNavigate } from "react-router-dom";

interface PickedFile {
  id: string;
  name: string;
  mimeType: string;
}

export default function SetupPage() {
  const [selectedFiles, setSelectedFiles] = useState<PickedFile[]>([]);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const handleSaveSelection = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.saveFiles(selectedFiles.map((f) => f.id));
      setMessage({ type: "success", text: `Saved ${selectedFiles.length} file(s) for sync!` });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <div className="card">
        <h2>1. Select Files to Sync</h2>
        <p style={{ color: "#666", marginBottom: 16, fontSize: 14 }}>
          Pick Google Docs, Sheets, PDFs, or DOCX files from your Drive.
        </p>

        <GooglePickerButton
          selectedFiles={selectedFiles}
          onFilesSelected={setSelectedFiles}
        />

        {selectedFiles.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <button
              className="btn btn-primary"
              onClick={handleSaveSelection}
              disabled={saving}
            >
              {saving ? "Saving..." : `Save Selection (${selectedFiles.length} files)`}
            </button>
          </div>
        )}

        {message && (
          <div className={`message ${message.type}`} style={{ marginTop: 12 }}>
            {message.text}
          </div>
        )}
      </div>

      <div className="card">
        <h2>2. Connect Notion (Optional)</h2>
        <p style={{ color: "#666", marginBottom: 16, fontSize: 14 }}>
          Sync pages and databases from your Notion workspace.
        </p>
        <NotionSetup />
      </div>

      <div className="card">
        <h2>3. Configure Pinecone</h2>
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
