import { useCallback, useRef, useState } from "react";

/** Shared chat state for the Info page chat and the timeline's AI Assistant. `onAsk(question)` -> Promise<string>. */
export function useChat(onAsk, greeting) {
  const nextId = useRef(1);
  const makeMessage = (role, text) => ({ id: nextId.current++, role, text });

  const [messages, setMessages] = useState(() => (greeting ? [{ id: 0, role: "assistant", text: greeting }] : []));
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);

  const send = useCallback(async () => {
    const question = draft.trim();
    if (!question || isSending) return;

    setMessages((m) => [...m, makeMessage("user", question)]);
    setDraft("");
    setIsSending(true);
    try {
      const answer = await onAsk(question);
      setMessages((m) => [...m, makeMessage("assistant", answer)]);
    } catch {
      setMessages((m) => [...m, makeMessage("assistant", "Sorry, something went wrong. Please try again.")]);
    } finally {
      setIsSending(false);
    }
  }, [draft, isSending, onAsk]);

  return { messages, draft, setDraft, isSending, send };
}
