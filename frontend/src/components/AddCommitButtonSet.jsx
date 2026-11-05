import styles from "./AddCommitButtonSet.module.css";

const AddCommitButtonSet = () => {
  return (
    <div className={styles.addCommitButton}>
      <div className={styles.property1addcommitProperty}>
        <div className={styles.addCommitButtonInner}>
          <div className={styles.instanceChild} />
        </div>
        <b className={styles.addCommit}>Add Commit</b>
      </div>
      <div className={styles.property1addcommitProperty2}>
        <div className={styles.addCommitButtonChild}>
          <div className={styles.instanceItem} />
        </div>
        <b className={styles.addCommit}>Add Commit</b>
      </div>
    </div>
  );
};

export default AddCommitButtonSet;
