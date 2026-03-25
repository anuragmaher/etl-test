import { useState, useRef, useEffect } from "react";
import { api } from "../api";

interface Source {
  title: string;
  doc_id: string;
  url: string;
  source_type: string;
  chunk_index: number;
  text: string;
  score: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  method?: string;
  sql_query?: string;
}

export default function AskPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      // Build history from previous messages
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await api.ask(question, history);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sources: res.sources, method: res.method, sql_query: res.sql_query },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="ask-panel">
      <div className="ask-header">
        <h3>Ask AI</h3>
        <span className="ask-subtitle">Ask questions about your synced documents</span>
      </div>

      <div className="ask-messages">
        {messages.length === 0 && (
          <div className="ask-empty">
            <p>Ask a question about your documents.</p>
            <p className="ask-hint">e.g. "What AI features does the product have?"</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`ask-message ${msg.role}`}>
            <div className="ask-message-content">
              {msg.content}
            </div>
            {msg.method && (
              <div className="ask-method">
                {msg.method === "sql" ? "via SQL query" : "via document search"}
              </div>
            )}
            {msg.sql_query && (
              <div className="ask-sql">
                <code>{msg.sql_query}</code>
              </div>
            )}
            {msg.sources && msg.sources.length > 0 && (
              <div className="ask-sources">
                <span className="ask-sources-label">Sources:</span>
                {msg.sources.map((src, j) => (
                  <a
                    key={j}
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ask-source-chip"
                    title={`${src.title} (score: ${src.score})`}
                  >
                    {src.title}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="ask-message assistant">
            <div className="ask-message-content ask-typing">Thinking...</div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="ask-input-area">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          rows={2}
          disabled={loading}
        />
        <button className="btn btn-primary" onClick={handleSend} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
