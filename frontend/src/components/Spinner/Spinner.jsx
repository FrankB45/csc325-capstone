import styles from "./Spinner.module.css";

const Spinner = ({ size = 24, label = "Loading" }) => (
  <span
    className={styles.spinner}
    style={{ width: size, height: size }}
    role="status"
    aria-label={label}
  />
);

export default Spinner;
