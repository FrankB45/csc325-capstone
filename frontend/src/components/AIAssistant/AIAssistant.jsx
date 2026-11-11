import { useEffect, useId, useRef, useState } from "react";
import { useChat } from "../../hooks/useChat.js";
import styles from "./AIAssistant.module.css";

const GREETING = "Hi! Ask me what changed between commits, or which ones are worth highlighting.";

/** Purple panel docked to the bottom-right; the header toggles it open. `onAsk(question)` -> Promise<string>. */
const AIAssistant = ({ onAsk }) => {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const { messages, draft, setDraft, isSending, send } = useChat(onAsk, GREETING);
  const logRef = useRef(null);

  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [messages, open]);

  return (
    <section className={styles.dock} aria-label="AI Assistant">
      <button
        type="button"
        className={styles.header}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={styles.dot} aria-hidden="true" />
        AI Assistant
      </button>

      <div id={panelId} className={styles.body} hidden={!open}>
        <div className={styles.log} ref={logRef} role="log" aria-live="polite">
          {messages.map((m) => (
            <p key={m.id} className={`${styles.bubble} ${m.role === "user" ? styles.user : ""}`}>{m.text}</p>
          ))}
        </div>
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <input
            className={styles.input}
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="What changed visually?"
            aria-label="Question for the AI Assistant"
          />
          <button
                    className={styles.submit}
                    type="submit"
                    disabled={isSending || !draft.trim()}
                  >
                    {isSending ? "Thinking…" : "Send"}
                  </button>
        </form>
      </div>
    </section>
  );
};

export default AIAssistant;
