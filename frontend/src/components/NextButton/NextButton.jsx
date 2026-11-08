import styles from "./NextButton.module.css";

/** Primary "Next" button. While `loading`, the label is replaced by three animated dots. */
const NextButton = ({
  type = "submit",
  loading = false,
  disabled = false,
  loadingLabel = "Loading",
  children = "Next",
  ...rest
}) => (
  <button
    type={type}
    className={styles.button}
    disabled={disabled || loading}
    aria-busy={loading || undefined}
    {...rest}
  >
    {loading ? (
      <span className={styles.dots} role="status" aria-label={loadingLabel}>
        <span />
        <span />
        <span />
      </span>
    ) : (
      children
    )}
  </button>
);

export default NextButton;
