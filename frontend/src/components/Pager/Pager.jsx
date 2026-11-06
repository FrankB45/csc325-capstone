import styles from "./Pager.module.css";

/** Dot pagination. `page` is 0-based. */
const Pager = ({ pageCount, page, onChange }) => (
  <nav className={styles.pager} aria-label="Gallery pages">
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
  </nav>
);

export default Pager;
