import styles from "./SyncUpdatesButtonSet.module.css";

const SyncUpdatesButtonSet = () => {
  return (
    <div className={styles.syncUpdatesButton}>
      <div className={styles.statedefault}>
        <div className={styles.statedefaultInner}>
          <div className={styles.instanceChild} />
        </div>
        <b className={styles.syncUpdates}>Sync Updates</b>
        <img className={styles.vectorIcon} alt="" />
      </div>
      <div className={styles.stateonhover}>
        <div className={styles.stateonhoverInner}>
          <div className={styles.instanceItem} />
        </div>
        <b className={styles.syncUpdates}>Sync Updates</b>
        <img className={styles.vectorIcon} alt="" />
      </div>
      <div className={styles.stateoff}>
        <div className={styles.stateonhoverInner}>
          <div className={styles.instanceInner} />
        </div>
        <b className={styles.syncUpdates}>Sync Updates</b>
        <img className={styles.vectorIcon} alt="" />
      </div>
      <div className={styles.statespinning}>
        <div className={styles.statedefaultInner}>
          <div className={styles.instanceItem} />
        </div>
        <b className={styles.syncUpdates}>Sync Updates</b>
        <img className={styles.vectorIcon} alt="" />
      </div>
    </div>
  );
};

export default SyncUpdatesButtonSet;
