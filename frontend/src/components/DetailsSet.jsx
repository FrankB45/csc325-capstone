import styles from "./DetailsSet.module.css";

const DetailsSet = () => {
  return (
    <div className={styles.details}>
      <div className={styles.statedefault}>
        <div className={styles.details2}>{`Details `}</div>
        <img className={styles.statedefaultChild} alt="" />
      </div>
      <div className={styles.stateopen1}>
        <img className={styles.stateopen1Child} alt="" />
        <div className={styles.detailsWelcomeToContainer}>
          <span>
            Details <br />
            <br />
          </span>
          <span className={styles.welcomeToMy}>
            Welcome to my personal portfolio. I am a Full-Stack Developer
            specializing in building scalable web applications, intuitive user
            interfaces, and efficient software solutions. Explore my recent
            projects, technical skill set, and professional background, or get
            in touch to collaborate.
          </span>
        </div>
      </div>
      <div className={styles.stateopen2}>
        <img className={styles.stateopen1Child} alt="" />
        <div className={styles.detailsWelcomeToContainer}>
          <span>
            Details <br />
            <br />
          </span>
          <span className={styles.streamlineYourDay}>
            Streamline your day and get things done. To-Do List is a simple,
            intuitive task manager built to help you organize daily tasks, set
            priorities, and stay focused on what matters most—without the
            clutter.
          </span>
        </div>
      </div>
      <div className={styles.stateopen3}>
        <img className={styles.stateopen3Child} alt="" />
        <div className={styles.detailsWelcomeToContainer}>
          <span>
            Details <br />
            <br />
          </span>
          <span className={styles.streamlineYourDay}>
            The description wasn’t added.
          </span>
        </div>
      </div>
    </div>
  );
};

export default DetailsSet;
