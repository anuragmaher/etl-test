import { useEffect, useRef, useState } from "react";
import { api } from "../api";

interface Folder {
  id: string;
  name: string;
}

interface Props {
  selectedFolders: Folder[];
  onFoldersSelected: (folders: Folder[]) => void;
}

declare global {
  interface Window {
    gapi: any;
    google: any;
  }
}

export default function GooglePickerButton({ selectedFolders, onFoldersSelected }: Props) {
  const [pickerReady, setPicker] = useState(false);
  const tokenRef = useRef<{ access_token: string; api_key: string; app_id: string } | null>(null);

  useEffect(() => {
    // Load Google Picker API
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

    const view = new window.google.picker.DocsView(window.google.picker.ViewId.FOLDERS)
      .setSelectFolderEnabled(true)
      .setMimeTypes("application/vnd.google-apps.folder");

    const picker = new window.google.picker.PickerBuilder()
      .setTitle("Select folders to sync")
      .addView(view)
      .enableFeature(window.google.picker.Feature.MULTISELECT_ENABLED)
      .setOAuthToken(access_token)
      .setDeveloperKey(api_key)
      .setAppId(app_id)
      .setCallback((data: any) => {
        if (data.action === window.google.picker.Action.PICKED) {
          const newFolders = data.docs
            .filter((d: any) => !selectedFolders.find((f) => f.id === d.id))
            .map((d: any) => ({ id: d.id, name: d.name }));
          onFoldersSelected([...selectedFolders, ...newFolders]);
        }
      })
      .build();

    picker.setVisible(true);
  };

  return (
    <div>
      <button className="btn btn-primary" onClick={openPicker} disabled={!pickerReady}>
        {pickerReady ? "Open Folder Picker" : "Loading Picker..."}
      </button>

      {selectedFolders.length > 0 && (
        <div style={{ marginTop: 16 }}>
          {selectedFolders.map((f) => (
            <span key={f.id} className="folder-tag">
              {f.name}
              <button onClick={() => onFoldersSelected(selectedFolders.filter((x) => x.id !== f.id))}>
                ✕
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
