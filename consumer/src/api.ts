const API_BASE = "http://localhost:8000";

async function request(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  // Auth
  authStatus: () => request("/auth/status"),
  exchangeCode: (code: string, redirectUri: string) =>
    request("/auth/google", {
      method: "POST",
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
    }),
  getToken: () => request("/auth/token"),

  // Folders
  listFolders: () => request("/folders"),

  // Files
  listFolderFiles: (folderId: string) => request(`/folders/${folderId}/files`),

  // Config
  getConfig: () => request("/config"),
  saveFolders: (folderIds: string[]) =>
    request("/config/folders", {
      method: "POST",
      body: JSON.stringify({ folder_ids: folderIds }),
    }),
  saveFiles: (fileIds: string[]) =>
    request("/config/files", {
      method: "POST",
      body: JSON.stringify({ file_ids: fileIds }),
    }),
  savePinecone: (config: { api_key: string; index_name: string; openai_api_key: string }) =>
    request("/config/pinecone", {
      method: "POST",
      body: JSON.stringify(config),
    }),

  // Notion
  notionStatus: () => request("/notion/status"),
  saveNotionToken: (token: string) =>
    request("/notion/token", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  listNotionPages: () => request("/notion/pages"),
  saveNotionPages: (pageIds: string[]) =>
    request("/notion/pages", {
      method: "POST",
      body: JSON.stringify({ page_ids: pageIds }),
    }),

  // Ask
  ask: (question: string, history: { role: string; content: string }[] = []) =>
    request("/ask", {
      method: "POST",
      body: JSON.stringify({ question, history }),
    }),

  // Sync
  triggerSync: () => request("/sync", { method: "POST" }),
  syncStatus: () => request("/sync/status"),
  listDocuments: () => request("/documents"),
  deleteDocument: (sourceType: string, docId: string) =>
    request(`/documents/${sourceType}/${docId}`, { method: "DELETE" }),
};
