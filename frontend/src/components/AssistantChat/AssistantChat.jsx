import { useEffect, useRef, useState } from "react";
import styles from "./AssistantChat.module.css";

const GREETING = {
  id: "greeting",
  role: "assistant",
  text: "Hi! I’m the Git Gallery assistant. Ask me anything about how the app works, what repos are supported, or how to get started.",
};

/** Chat panel. `onAsk(question)` returns a promise of the assistant's answer text. */
const AssistantChat = ({ onAsk }) => {
  const [messages, setMessages] = useState([GREETING]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const logRef = useRef(null);

  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [messages]);

  async function handleSubmit(e) {
    e.preventDefault();
    const question = draft.trim();
    if (!question || isSending) return;

    setMessages((m) => [...m, { id: crypto.randomUUID(), role: "user", text: question }]);
    setDraft("");
    setIsSending(true);
    try {
      const answer = await onAsk(question);
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: "assistant", text: answer }]);
    } catch {
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: "assistant", text: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className={styles.panel} aria-label="Git Gallery Assistant">
      <header className={styles.header}>
        <span className={styles.dot} aria-hidden="true" />
        <span className={styles.name}>Git Gallery Assistant</span>
        <span className={styles.tag} aria-hidden="true">AI</span>
      </header>

      <div className={styles.log} ref={logRef} role="log" aria-live="polite">
        {messages.map((m) => (
          <p key={m.id} className={`${styles.bubble} ${m.role === "user" ? styles.user : ""}`}>
            {m.text}
          </p>
        ))}
      </div>

      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          className={styles.input}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask something about Git Gallery…"
          aria-label="Ask something about Git Gallery"
        />
        <button
          className={styles.submit}
          type="submit"
          disabled={isSending || !draft.trim()}
        >
          {isSending ? "Thinking…" : "Send"}
        </button>
      </form>
    </section>
  );
}

export default AssistantChat;
