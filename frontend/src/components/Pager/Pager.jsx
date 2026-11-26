import styles from "./Pager.module.css";

/** Dot pagination. `page` is 0-based. */
const Pager = ({ pageCount, page, onChange }) => (
  <nav className={styles.pager} aria-label="Gallery pages">
    <button
      type="button"
      className={styles.control}
      aria-label="First page"
      onClick={() => onChange(0)}
      disabled={page === 0}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 5v14M19 6l-6 6 6 6M13 6l-6 6 6 6" />
      </svg>
    </button>
    <button
      type="button"
      className={styles.control}
      aria-label="Previous page"
      onClick={() => onChange(page - 1)}
      disabled={page === 0}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m15 5-7 7 7 7" />
      </svg>
    </button>
    {Array.from({ length: pageCount }, (_, i) => (
      <button
        key={i}
        type="button"
        className={`${styles.dot} ${i === page ? styles.active : ""}`}
        aria-label={`Page ${i + 1}`}
        aria-current={i === page ? "page" : undefined}
        onClick={() => onChange(i)}
      />
    ))}
    <button
      type="button"
      className={styles.control}
      aria-label="Next page"
      onClick={() => onChange(page + 1)}
      disabled={page === pageCount - 1}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m9 5 7 7-7 7" />
      </svg>
    </button>
    <button
      type="button"
      className={styles.control}
      aria-label="Last page"
      onClick={() => onChange(pageCount - 1)}
      disabled={page === pageCount - 1}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M18 5v14M5 6l6 6-6 6m6-12 6 6-6 6" />
      </svg>
    </button>
  </nav>
);

export default Pager;
