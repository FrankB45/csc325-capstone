import { formatShortDate } from "../../utils/format.js";
import styles from "./Timeline.module.css";

/**
 * Horizontal commit timeline. Each commit is a thumbnail + point + date.
 * - Clicking a thumbnail selects it (`selectedIds` can hold 1 id in Standard, 2 in Compare).
 * - The small expand button opens the full-size screenshot (`onExpand`).
 */
const Timeline = ({ commits, selectedIds, onSelect, onExpand }) => (
  <ol className={styles.timeline} aria-label="Commit timeline">
    {commits.map((commit) => {
      const selected = selectedIds.includes(commit.id);
      return (
        <li key={commit.id} className={styles.item}>
          <div className={styles.thumbWrap}>
            <button
              type="button"
              className={`${styles.thumb} ${selected ? styles.thumbSelected : ""}`}
              aria-pressed={selected}
              aria-label={`Select commit: ${commit.message}`}
              onClick={() => onSelect(commit.id)}
            >
              <img src={commit.image} alt="" />
            </button>
            <button
              type="button"
              className={styles.expand}
              aria-label={`View full screenshot: ${commit.message}`}
              onClick={() => onExpand(commit)}
            >
              ⤢
            </button>
          </div>
          <span className={`${styles.point} ${selected ? styles.pointSelected : ""}`} aria-hidden="true" />
          <time className={styles.date} dateTime={commit.date}>
            {formatShortDate(commit.date)}
          </time>
        </li>
      );
    })}
  </ol>
);

export default Timeline;
