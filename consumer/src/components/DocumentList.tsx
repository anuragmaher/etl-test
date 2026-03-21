interface Document {
  doc_id: string;
  title: string;
  source_type: string;
  last_modified: string;
  synced_at: string;
}

interface Props {
  documents: Document[];
}

export default function DocumentList({ documents }: Props) {
  if (documents.length === 0) {
    return <p style={{ color: "#999" }}>No documents synced yet. Click "Sync Now" to start.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Type</th>
          <th>Last Modified</th>
          <th>Synced At</th>
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr key={doc.doc_id}>
            <td>{doc.title}</td>
            <td>{doc.source_type}</td>
            <td>{new Date(doc.last_modified).toLocaleString()}</td>
            <td>{new Date(doc.synced_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
