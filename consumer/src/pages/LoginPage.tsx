import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const REDIRECT_URI = window.location.origin + "/auth/callback";
const SCOPES = "https://www.googleapis.com/auth/documents.readonly https://www.googleapis.com/auth/drive.readonly";

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    // Check if this is an OAuth callback
    const code = searchParams.get("code");
    if (code) {
      api.exchangeCode(code, REDIRECT_URI).then(() => {
        navigate("/setup");
      }).catch((err) => {
        console.error("Auth failed:", err);
      });
      return;
    }

    // Check if already authenticated
    api.authStatus().then((res) => {
      if (res.authenticated) {
        navigate("/setup");
      }
    }).catch(() => {});
  }, [searchParams, navigate]);

  const handleLogin = () => {
    const params = new URLSearchParams({
      client_id: GOOGLE_CLIENT_ID,
      redirect_uri: REDIRECT_URI,
      response_type: "code",
      scope: SCOPES,
      access_type: "offline",
      prompt: "consent",
    });
    window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
  };

  // If we have a code, show loading
  if (searchParams.get("code")) {
    return (
      <div className="center-page">
        <h1>Signing in...</h1>
        <p>Please wait while we complete authentication.</p>
      </div>
    );
  }

  return (
    <div className="center-page">
      <h1>ETL Pipeline</h1>
      <p>Sync your Google Drive documents to Pinecone for RAG</p>
      <button className="btn btn-primary" onClick={handleLogin} style={{ padding: "14px 36px", fontSize: 16 }}>
        Sign in with Google
      </button>
    </div>
  );
}
