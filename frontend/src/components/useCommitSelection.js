import { useMemo, useState } from "react";
import { MAX_SELECTED, MIN_SELECTED, RULE_MESSAGE, defaultSelection } from "./commitSelection";

export function useCommitSelection(commits) {
  const [selected, setSelected] = useState(() => new Set(defaultSelection(commits)));
  const [error, setError] = useState(null);

  const toggle = (sha) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(sha)) {
        next.delete(sha);
        setError(null);
      } else if (next.size >= MAX_SELECTED) {
        setError(RULE_MESSAGE); // AC4: explain the limit, don't add
        return prev;
      } else {
        next.add(sha);
        setError(null);
      }
      return next;
    });
  };

  // Selected SHAs in history order (what gets submitted).
  const ordered = useMemo(
    () => commits.filter((c) => selected.has(c.sha)).map((c) => c.sha),
    [commits, selected]
  );

  // AC4: returns the SHAs to submit, or null (and sets the error) if invalid.
  const validate = () => {
    if (ordered.length < MIN_SELECTED || ordered.length > MAX_SELECTED) {
      setError(RULE_MESSAGE);
      return null;
    }
    setError(null);
    return ordered;
  };

  return { selected, count: ordered.length, error, toggle, validate };
}