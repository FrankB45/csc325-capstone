import styles from "./LoadingDots.module.css";

const LoadingDots = ({ label = "Loading" }) => (
  <span className={styles.dots} role="status" aria-label={label}>
    <span />
    <span />
    <span />
  </span>
);

export default LoadingDots;
