import { useId, useState } from "react";
import Button from "../AIAssistantButton.jsx";
import styles from "./AIAssistant.module.css";

/** Collapsible assistant panel. `onAsk(question)` should return a promise of the answer text. */
const AIAssistant = ({ onAsk }) => {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const panelId = useId();

  async function handleSubmit(e) {
    e.preventDefault();
    if (!question.trim() || isAsking) return;
    setIsAsking(true);
    try {
      setAnswer(await onAsk(question.trim()));
      setQuestion("");
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className={styles.wrapper}>
      {open && (
        <section id={panelId} className={styles.panel} aria-label="AI Assistant">
          <p className={styles.intro}>
            Ask me about the visual changes between commits, or which commits to highlight for stakeholders.
          </p>
          {answer && <p className={styles.answer} role="status">{answer}</p>}
          <form className={styles.form} onSubmit={handleSubmit}>
            <input
              className={styles.input}
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What changed visually?"
              aria-label="Question for the AI Assistant"
            />
            <Button type="submit" size="sm" loading={isAsking}>Ask</Button>
          </form>
        </section>
      )}
      <Button
        variant="secondary"
        size="md"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        AI Assistant
      </Button>
    </div>
  );
};

export default AIAssistant;
