import styles from "./DetailsButton.module.css";

/** "Details ▸" disclosure toggle; the arrow turns down when `expanded`. */
const DetailsButton = ({ expanded, controls, onClick, children = "Details" }) => (
  <button
    type="button"
    className={styles.button}
    aria-expanded={expanded}
    aria-controls={controls}
    onClick={onClick}
  >
    {children}
    <span className={`${styles.arrow} ${expanded ? styles.open : ""}`} aria-hidden="true" />
  </button>
);

export default DetailsButton;
