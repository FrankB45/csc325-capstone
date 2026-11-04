import { useCallback } from "react";
import styles from "./TimelineModeButtonSet.module.css";

const TimelineModeButtonSet = () => {
  const onStateCompareContainerClick = useCallback(() => {
    // Add your code here
  }, []);

  return (
    <div className={styles.timelineModeButton}>
      <div
        className={styles.statecompare}
        onClick={onStateCompareContainerClick}
      >
        <div className={styles.statecompareChild} />
        <div className={styles.statecompareItem} />
        <b className={styles.standard}>Standard</b>
        <b className={styles.compare}>Compare</b>
      </div>
      <div
        className={styles.statestandard}
        onClick={onStateCompareContainerClick}
      >
        <div className={styles.statecompareChild} />
        <div className={styles.statestandardItem} />
        <b className={styles.standard}>Standard</b>
        <b className={styles.compare2}>Compare</b>
      </div>
    </div>
  );
};

export default TimelineModeButtonSet;
