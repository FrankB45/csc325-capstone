import { formatDate } from "../../utils/format.js";
import { MAX_COMMITS, MIN_COMMITS } from "../../utils/commits.js";
import styles from "./CommitPicker.module.css";

/** Controlled checklist; selection is limited to MIN_COMMITS..MAX_COMMITS. */
const CommitPicker = ({ commits, selectedIds, onChange }) => {
  const count = selectedIds.length;
  const atMax = count >= MAX_COMMITS;

  const toggle = (id) =>
    onChange(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id]);

  return (
    <fieldset className={styles.fieldset}>
      <legend className={styles.legend}>Commits Included</legend>
      <p className={`${styles.count} ${count < MIN_COMMITS ? styles.countError : ""}`} aria-live="polite">
        {count} of {MAX_COMMITS} selected{count < MIN_COMMITS ? " — select at least one" : ""}
      </p>
      <ul className={styles.list}>
        {commits.map((c) => {
          const checked = selectedIds.includes(c.id);
          return (
            <li key={c.id}>
              <label className={styles.row}>
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={!checked && atMax}
                  onChange={() => toggle(c.id)}
                />
                <span className={styles.message}>{c.message}</span>
                <span className={styles.meta}>{c.sha.slice(0, 7)} · {formatDate(c.date)}</span>
              </label>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
};

export default CommitPicker;
