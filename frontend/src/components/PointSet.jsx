import styles from "./PointSet.module.css";

const PointSet = () => {
  return (
    <div className={styles.point}>
      <div className={styles.statedefault}>
        <div className={styles.statedefaultChild} />
      </div>
      <div className={styles.stateselected}>
        <div className={styles.stateselectedChild} />
      </div>
    </div>
  );
};

export default PointSet;
