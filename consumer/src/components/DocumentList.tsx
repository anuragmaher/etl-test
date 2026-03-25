import { useState } from "react";
import { api } from "../api";

interface Document {
  doc_id: string;
  title: string;
  source_type: string;
  last_modified: string;
  synced_at: string;
}

interface Props {
  documents: Document[];
  onDocumentDeleted?: () => void;
}

export default function DocumentList({ documents, onDocumentDeleted }: Props) {
  const [deleting, setDeleting] = useState<string | null>(null);

  if (documents.length === 0) {
    return <p style={{ color: "#999" }}>No documents synced yet. Click "Sync Now" to start.</p>;
  }

  const handleDelete = async (doc: Document) => {
    if (!confirm(`Remove "${doc.title}" from synced documents? This will also delete it from Pinecone.`)) {
      return;
    }

    setDeleting(doc.doc_id);
    try {
      await api.deleteDocument(doc.source_type, doc.doc_id);
      onDocumentDeleted?.();
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Type</th>
          <th>Last Modified</th>
          <th>Synced At</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr key={doc.doc_id}>
            <td>{doc.title}</td>
            <td>{doc.source_type}</td>
            <td>{new Date(doc.last_modified).toLocaleString()}</td>
            <td>{new Date(doc.synced_at).toLocaleString()}</td>
            <td>
              <button
                className="btn-delete"
                onClick={() => handleDelete(doc)}
                disabled={deleting === doc.doc_id}
                title="Remove document"
              >
                {deleting === doc.doc_id ? "..." : "✕"}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
