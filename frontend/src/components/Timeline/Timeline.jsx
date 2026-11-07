import { useCallback, useEffect, useRef, useState } from "react";
import ArrowButton from "../ArrowButton/ArrowButton.jsx";
import { formatShortDate } from "../../utils/format.js";
import styles from "./Timeline.module.css";

/**
 * Horizontal commit timeline: a line with one point per commit, date + short SHA underneath.
 * Commits must be ordered oldest -> newest. The arrows scroll the track when there are more commits than fit.
 */
const Timeline = ({ commits, selectedIds, onSelect }) => {
  const trackRef = useRef(null);
  const [edges, setEdges] = useState({ atStart: true, atEnd: true });

  const updateEdges = useCallback(() => {
    const el = trackRef.current;
    if (!el) return;
    setEdges({
      atStart: el.scrollLeft <= 1,
      atEnd: el.scrollLeft + el.clientWidth >= el.scrollWidth - 1,
    });
  }, []);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return undefined;
    const frame = requestAnimationFrame(updateEdges);
    el.addEventListener("scroll", updateEdges, { passive: true });
    const observer = new ResizeObserver(updateEdges);
    observer.observe(el);
    return () => {
      cancelAnimationFrame(frame);
      el.removeEventListener("scroll", updateEdges);
      observer.disconnect();
    };
  }, [updateEdges, commits.length]);

  const scrollByPage = (direction) => {
    const el = trackRef.current;
    el?.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: "smooth" });
  };

  return (
    <div className={styles.wrapper}>
      <ArrowButton direction="left" disabled={edges.atStart} onClick={() => scrollByPage(-1)} />

      <div className={styles.track} ref={trackRef}>
        <ol className={styles.list} aria-label="Commit timeline">
          {commits.map((commit) => {
            const selected = selectedIds.includes(commit.id);
            return (
              <li key={commit.id} className={styles.item}>
                <button
                  type="button"
                  className={styles.hit}
                  aria-pressed={selected}
                  aria-label={`Select commit ${commit.sha.slice(0, 7)}: ${commit.message}`}
                  onClick={() => onSelect(commit.id)}
                >
                  <span className={`${styles.point} ${selected ? styles.pointSelected : ""}`} />
                  <span className={styles.label}>
                    <time dateTime={commit.date}>{formatShortDate(commit.date)}</time>
                    <span>({commit.sha.slice(0, 7)})</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>

      <ArrowButton direction="right" disabled={edges.atEnd} onClick={() => scrollByPage(1)} />
    </div>
  );
};

export default Timeline;
