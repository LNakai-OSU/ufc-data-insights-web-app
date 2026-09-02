import { useRef, useState } from "react";
import { askChat } from "../api";
import GloveLoader from "./GloveLoader";

const EXAMPLE_QUESTIONS = [
  "Do southpaws have a higher win rate than orthodox fighters?",
  "Who has the most submission wins?",
  "What's the most common way fights end in the heavyweight division?",
];

export default function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [askedQuestion, setAskedQuestion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const textareaRef = useRef(null);

  async function submit(q) {
    const text = (q ?? question).trim();
    if (!text || loading) return;
    setAskedQuestion(text);
    setQuestion("");
    setError(null);
    setResult(null);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setLoading(true);
    try {
      const res = await askChat(text);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleInput(e) {
    setQuestion(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const hasConversation = askedQuestion !== null;

  return (
    <div className="panel claude-chat-panel">
      <h3>Ask the stats assistant</h3>

      {hasConversation && (
        <div className="claude-conversation">
          <div className="claude-turn-user">{askedQuestion}</div>

          {loading && <GloveLoader size="sm" label="Consulting the judges" />}

          {error && (
            <div className="error-text">
              {error}
              {error.includes("Chat assistant unavailable") && (
                <div className="muted">(This requires ANTHROPIC_API_KEY to be set on the backend.)</div>
              )}
            </div>
          )}

          {result && (
            <div className="claude-turn-assistant">
              <p>{result.answer}</p>
              {result.queries?.length > 0 && (
                <details className="claude-tool-chip">
                  <summary>
                    <span className="claude-tool-icon">⌁</span>
                    Queried the database · {result.queries.length}{" "}
                    {result.queries.length === 1 ? "query" : "queries"}
                  </summary>
                  {result.queries.map((q, i) => (
                    <pre key={i} className="sql-block">
                      {q.sql}
                      {"\n"}
                      <span className="muted">-- {q.row_count} rows</span>
                    </pre>
                  ))}
                </details>
              )}
            </div>
          )}
        </div>
      )}

      <div className="claude-composer">
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder="Ask a question about UFC fighters or fights..."
          value={question}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          className="claude-composer-input"
        />
        <button
          className="claude-send-btn"
          onClick={() => submit()}
          disabled={loading || !question.trim()}
          aria-label="Ask"
        >
          ↑
        </button>
      </div>

      {!hasConversation && (
        <div className="claude-suggestions">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button key={q} className="claude-suggestion-card" onClick={() => submit(q)}>
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
