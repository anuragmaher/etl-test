import { useEffect, useRef, useState } from "react";
import { api } from "../api";

interface PickedFile {
  id: string;
  name: string;
  mimeType: string;
}

interface Props {
  selectedFiles: PickedFile[];
  onFilesSelected: (files: PickedFile[]) => void;
}

declare global {
  interface Window {
    gapi: any;
    google: any;
  }
}

const SUPPORTED_MIMES = [
  "application/vnd.google-apps.document",
  "application/vnd.google-apps.spreadsheet",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/pdf",
].join(",");

function getFileIcon(mimeType: string) {
  if (mimeType.includes("spreadsheet") || mimeType.includes("sheet")) return "📊";
  if (mimeType.includes("pdf")) return "📕";
  if (mimeType.includes("wordprocessing") || mimeType.includes("docx")) return "📝";
  return "📄";
}

export default function GooglePickerButton({ selectedFiles, onFilesSelected }: Props) {
  const [pickerReady, setPicker] = useState(false);
  const tokenRef = useRef<{ access_token: string; api_key: string; app_id: string } | null>(null);

  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://apis.google.com/js/api.js";
    script.onload = () => {
      window.gapi.load("picker", () => setPicker(true));
    };
    document.head.appendChild(script);
  }, []);

  const openPicker = async () => {
    if (!tokenRef.current) {
      tokenRef.current = await api.getToken();
    }
    const { access_token, api_key, app_id } = tokenRef.current!;

    // View for documents, spreadsheets, PDFs
    const docsView = new window.google.picker.DocsView()
      .setIncludeFolders(true)
      .setSelectFolderEnabled(false)
      .setMimeTypes(SUPPORTED_MIMES);

    // Shared drives view
    const sharedView = new window.google.picker.DocsView()
      .setIncludeFolders(true)
      .setSelectFolderEnabled(false)
      .setMimeTypes(SUPPORTED_MIMES)
      .setEnableDrives(true);

    const picker = new window.google.picker.PickerBuilder()
      .setTitle("Select files to sync")
      .addView(docsView)
      .addView(sharedView)
      .enableFeature(window.google.picker.Feature.MULTISELECT_ENABLED)
      .enableFeature(window.google.picker.Feature.SUPPORT_DRIVES)
      .setOAuthToken(access_token)
      .setDeveloperKey(api_key)
      .setAppId(app_id)
      .setCallback((data: any) => {
        if (data.action === window.google.picker.Action.PICKED) {
          const newFiles = data.docs
            .filter((d: any) => !selectedFiles.find((f) => f.id === d.id))
            .map((d: any) => ({ id: d.id, name: d.name, mimeType: d.mimeType }));
          onFilesSelected([...selectedFiles, ...newFiles]);
        }
      })
      .build();

    picker.setVisible(true);
  };

  return (
    <div>
      <button className="btn btn-primary" onClick={openPicker} disabled={!pickerReady}>
        {pickerReady ? "Select Files" : "Loading Picker..."}
      </button>
      {selectedFiles.length > 0 && (
        <button className="btn btn-secondary" onClick={openPicker} disabled={!pickerReady} style={{ marginLeft: 12 }}>
          Add More
        </button>
      )}

      {selectedFiles.length > 0 && (
        <div style={{ marginTop: 16 }}>
          {selectedFiles.map((f) => (
            <span key={f.id} className="folder-tag">
              {getFileIcon(f.mimeType)} {f.name}
              <button onClick={() => onFilesSelected(selectedFiles.filter((x) => x.id !== f.id))}>
                ✕
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
