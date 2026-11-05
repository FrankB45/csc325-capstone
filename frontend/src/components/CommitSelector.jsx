import { MAX_SELECTED } from "./commitSelection";
import { useCommitSelection } from "./useCommitSelection";

// Matches the Figma "New Project Setup" -> "Commits Included" block.
// props:
//   commits  [{sha, message, date}] oldest -> newest
//   onNext   (shas: string[]) -> only called with a valid 1-10 selection
//   onCancel () -> optional
// SWAP-IN: replace the native <input type="checkbox"> and <button> with your
// existing Checkbox / Next Button components (keep the same onChange/onClick).
export default function CommitSelector({ commits, onNext, onCancel }) {
  const { selected, count, error, toggle, validate } = useCommitSelection(commits);

  const handleNext = () => {
    const shas = validate();
    if (shas) onNext(shas);
  };

  return (
    <section className="commit-selector" aria-labelledby="commits-included">
      <h3 id="commits-included">Commits Included</h3>

      {/* AC3: live selected count */}
      <p className="commit-count" aria-live="polite">
        {count} of {MAX_SELECTED} selected
      </p>

      <ul className="commit-list" style={{ listStyle: "none", padding: 0 }}>
        {commits.map((c) => (
          <li key={c.sha}>
            <label>
              <input
                type="checkbox"
                checked={selected.has(c.sha)}
                onChange={() => toggle(c.sha)}
              />{" "}
              {c.message} ({c.sha.slice(0, 7)})
            </label>
          </li>
        ))}
      </ul>

      {/* AC4: states the 1-10 requirement */}
      {error && (
        <p className="commit-error" role="alert">
          {error}
        </p>
      )}

      <div className="commit-actions">
        <button type="button" className="next-button" onClick={handleNext}>
          Next
        </button>
        {onCancel && (
          <button type="button" className="cancel-link" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </section>
  );
}
