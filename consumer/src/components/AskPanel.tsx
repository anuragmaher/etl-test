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

interface Step {
  thought: string;
  tool: string;
  tool_input: string;
  result: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  method?: string;
  sql_query?: string;
  steps?: Step[];
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
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await api.ask(question, history);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          method: res.method,
          sql_query: res.sql_query,
          steps: res.steps,
        },
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
        <span className="ask-subtitle">Agentic Q&A — searches docs and queries data</span>
      </div>

      <div className="ask-messages">
        {messages.length === 0 && (
          <div className="ask-empty">
            <p>Ask a question about your documents.</p>
            <p className="ask-hint">The AI agent will decide whether to search documents, query spreadsheets, or both.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`ask-message ${msg.role}`}>
            <div className="ask-message-content">
              {msg.content}
            </div>

            {msg.method && (
              <div className="ask-method">
                {msg.method}
              </div>
            )}

            {msg.sql_query && (
              <div className="ask-sql">
                <code>{msg.sql_query}</code>
              </div>
            )}

            {msg.steps && msg.steps.length > 0 && (
              <AgentSteps steps={msg.steps} />
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
            <div className="ask-message-content ask-typing">Agent is thinking...</div>
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

function AgentSteps({ steps }: { steps: Step[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="ask-steps">
      <button className="ask-steps-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? "▾" : "▸"} {steps.length} agent step{steps.length !== 1 ? "s" : ""}
      </button>
      {expanded && (
        <div className="ask-steps-list">
          {steps.map((step, i) => (
            <div key={i} className="ask-step">
              <div className="ask-step-thought">{step.thought}</div>
              <div className="ask-step-action">
                <span className="ask-step-tool">{step.tool}</span>
                {step.tool !== "final_answer" && (
                  <code className="ask-step-input">{step.tool_input}</code>
                )}
              </div>
              {step.result && (
                <div className="ask-step-result">{step.result}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
