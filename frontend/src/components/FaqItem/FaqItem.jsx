import styles from "./FaqItem.module.css";

/** Native <details>: keyboard + screen-reader friendly, and several items can be open at once. */
const FaqItem = ({ question, children }) => (
  <details className={styles.item}>
    <summary className={styles.summary}>
      <span>{question}</span>
      <span className={styles.icon} aria-hidden="true">+</span>
    </summary>
    <div className={styles.answer}>
      <p>{children}</p>
    </div>
  </details>
);

export default FaqItem;
