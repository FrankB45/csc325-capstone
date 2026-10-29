import styles from "./NextButtonSet.module.css";

const NextButtonSet = () => {
  return (
    <div className={styles.nextButton}>
      <div className={styles.property1nextProperty2de}>
        <div className={styles.nextButtonInner}>
          <div className={styles.instanceChild} />
        </div>
        <b className={styles.next}>Next</b>
      </div>
      <div className={styles.property1nextProperty2on}>
        <div className={styles.nextButtonChild}>
          <div className={styles.instanceItem} />
        </div>
        <b className={styles.next}>Next</b>
      </div>
    </div>
  );
};

export default NextButtonSet;
