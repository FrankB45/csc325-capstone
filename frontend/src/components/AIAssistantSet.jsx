import styles from "./AIAssistantSet.module.css";

const AIAssistantSet = () => {
  return (
    <div className={styles.aiAssistant}>
      <div className={styles.statedefault}>
        <div className={styles.button}>
          <div className={styles.container} />
          <div className={styles.aiAssistant2}>AI Assistant</div>
        </div>
      </div>
      <div className={styles.stateopen}>
        <div className={styles.container2}>
          <div className={styles.container3}>
            <div className={styles.container4}>
              <div className={styles.container5} />
              <div className={styles.text}>
                <div className={styles.aiAssistant3}>AI Assistant</div>
              </div>
            </div>
            <div className={styles.button2}>
              <img className={styles.icon} alt="" />
            </div>
          </div>
          <div className={styles.container6}>
            <div className={styles.paragraph}>
              <div className={styles.askMeAbout}>
                Ask me about the visual changes between commits, or which
                commits to highlight for stakeholders.
              </div>
            </div>
            <div className={styles.container7}>
              <div className={styles.textInput}>
                <div className={styles.whatChangedVisually}>
                  What changed visually?
                </div>
              </div>
              <div className={styles.button3}>
                <div className={styles.ask}>Ask</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistantSet;
