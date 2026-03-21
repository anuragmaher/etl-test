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

  // Sync
  triggerSync: () => request("/sync", { method: "POST" }),
  syncStatus: () => request("/sync/status"),
  listDocuments: () => request("/documents"),
};
