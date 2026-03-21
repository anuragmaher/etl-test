import { useState } from "react";
import Layout from "../components/Layout";
import GooglePickerButton from "../components/GooglePickerButton";
import FileTreeView from "../components/FileTreeView";
import PineconeConfigForm from "../components/PineconeConfigForm";
import { api } from "../api";
import { useNavigate } from "react-router-dom";

interface Folder {
  id: string;
  name: string;
}

export default function SetupPage() {
  const [selectedFolders, setSelectedFolders] = useState<Folder[]>([]);
  const [fileTree, setFileTree] = useState<any[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [selectedFileIds, setSelectedFileIds] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const handleFoldersSelected = async (folders: Folder[]) => {
    setSelectedFolders(folders);
    setFileTree([]);
    setSelectedFileIds(new Set());
    setMessage(null);

    if (folders.length === 0) return;

    setLoadingFiles(true);
    try {
      // Fetch files for all selected folders
      const trees = await Promise.all(
        folders.map(async (f) => {
          const res = await api.listFolderFiles(f.id);
          return { id: f.id, name: f.name, type: "folder" as const, mimeType: "", children: res.files };
        })
      );
      setFileTree(trees);
    } catch (err: any) {
      setMessage({ type: "error", text: `Failed to load files: ${err.message}` });
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleSaveSelection = async () => {
    setSaving(true);
    setMessage(null);
    try {
      // Save both folder IDs and selected file IDs
      await api.saveFolders(selectedFolders.map((f) => f.id));
      await api.saveFiles(Array.from(selectedFileIds));
      setMessage({ type: "success", text: `Saved ${selectedFileIds.size} file(s) for sync!` });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <div className="card">
        <h2>1. Select Google Drive Folders</h2>
        <p style={{ color: "#666", marginBottom: 16, fontSize: 14 }}>
          Choose a folder, then select which files to sync.
        </p>

        <GooglePickerButton
          selectedFolders={selectedFolders}
          onFoldersSelected={handleFoldersSelected}
        />

        {loadingFiles && (
          <p style={{ marginTop: 16, color: "#666" }}>Loading files...</p>
        )}

        {fileTree.length > 0 && !loadingFiles && (
          <>
            <FileTreeView
              nodes={fileTree}
              selectedIds={selectedFileIds}
              onSelectionChange={setSelectedFileIds}
            />

            <div style={{ marginTop: 16 }}>
              <button
                className="btn btn-primary"
                onClick={handleSaveSelection}
                disabled={saving || selectedFileIds.size === 0}
              >
                {saving ? "Saving..." : `Save Selection (${selectedFileIds.size} files)`}
              </button>
            </div>
          </>
        )}

        {message && (
          <div className={`message ${message.type}`} style={{ marginTop: 12 }}>
            {message.text}
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
