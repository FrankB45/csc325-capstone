import styles from "./ProjectsSet.module.css";

const ProjectsSet = () => {
  return (
    <div className={styles.projects}>
      <div className={styles.projectpersonalWebsiteStat}>
        <img className={styles.imageIcon} alt="" />
      </div>
      <div className={styles.projectpersonalWebsiteStat2}>
        <img className={styles.imageIcon2} alt="" />
      </div>
      <div className={styles.projecttoDoListStatedefa}>
        <img className={styles.imageIcon2} alt="" />
      </div>
      <div className={styles.projecttoDoListStateonho}>
        <img className={styles.imageIcon4} alt="" />
      </div>
      <div className={styles.projectweatherAppStatedef}>
        <img className={styles.imageIcon2} alt="" />
      </div>
      <div className={styles.projectweatherAppStateonh}>
        <img className={styles.imageIcon4} alt="" />
      </div>
    </div>
  );
};

export default ProjectsSet;
