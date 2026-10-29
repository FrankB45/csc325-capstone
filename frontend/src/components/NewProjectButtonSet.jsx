import styles from "./NewProjectButtonSet.module.css";

const NewProjectButtonSet = () => {
  return (
    <div className={styles.newProjectButton}>
      <div className={styles.buttonnewProjectStatedefa}>
        <div className={styles.newProjectButtonInner}>
          <div className={styles.instanceChild} />
        </div>
        <b className={styles.newProject}>New Project</b>
      </div>
      <div className={styles.buttonnewProjectStateonho}>
        <div className={styles.newProjectButtonInner}>
          <div className={styles.instanceItem} />
        </div>
        <b className={styles.newProject}>New Project</b>
      </div>
    </div>
  );
};

export default NewProjectButtonSet;
