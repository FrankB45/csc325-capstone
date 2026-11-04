import styles from "./CheckboxSet.module.css";

const CheckboxSet = () => {
  return (
    <div className={styles.checkbox}>
      <div className={styles.stateoff}>
        <div className={styles.stateoffChild} />
      </div>
      <div className={styles.stateon}>
        <div className={styles.stateoffChild} />
        <div className={styles.div}>✔</div>
      </div>
    </div>
  );
};

export default CheckboxSet;
