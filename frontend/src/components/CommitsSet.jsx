import { useState, useCallback } from "react";
import CommitOverlay from "../components/CommitOverlay";
import PortalPopup from "../components/PortalPopup";
import styles from "./CommitsSet.module.css";

const CommitsSet = () => {
  const [isCommitOverlayOpen, setCommitOverlayOpen] = useState(false);

  const openCommitOverlay = useCallback(() => {
    setCommitOverlayOpen(true);
  }, []);

  const closeCommitOverlay = useCallback(() => {
    setCommitOverlayOpen(false);
  }, []);

  return (
    <>
      <div className={styles.commits}>
        <img className={styles.commit1StatedefaultIcon} alt="" />
        <div className={styles.commit1Stateonhover} onClick={openCommitOverlay}>
          <img className={styles.commitsChild} alt="" />
          <img className={styles.maximize1Icon} alt="" />
        </div>
        <img className={styles.commit2StatedefaultIcon} alt="" />
        <div className={styles.commit2Stateonhover} onClick={openCommitOverlay}>
          <img className={styles.commitsChild} alt="" />
          <img className={styles.maximize1Icon} alt="" />
        </div>
        <img className={styles.commit3StatedefaultIcon} alt="" />
        <div className={styles.commit3Stateonhover} onClick={openCommitOverlay}>
          <img className={styles.commitsChild} alt="" />
          <img className={styles.maximize1Icon} alt="" />
        </div>
        <img className={styles.commit4StatedefaultIcon} alt="" />
        <div className={styles.commit4Stateonhover} onClick={openCommitOverlay}>
          <img className={styles.commitsChild} alt="" />
          <img className={styles.maximize1Icon} alt="" />
        </div>
        <img className={styles.commit5StatedefaultIcon} alt="" />
        <div className={styles.commit5Stateonhover} onClick={openCommitOverlay}>
          <img className={styles.commitsChild} alt="" />
          <img className={styles.maximize1Icon} alt="" />
        </div>
        <img className={styles.commit6StatedefaultIcon} alt="" />
        <div className={styles.commit6Stateonhover} onClick={openCommitOverlay}>
          <img className={styles.commitsChild} alt="" />
          <img className={styles.maximize1Icon} alt="" />
        </div>
        <img className={styles.commit7StatedefaultIcon} alt="" />
        <div className={styles.commit7Stateonhover} onClick={openCommitOverlay}>
          <img className={styles.commitsChild} alt="" />
          <img className={styles.maximize1Icon} alt="" />
        </div>
        <div className={styles.commitblank}>
          <div className={styles.commitblankChild} />
        </div>
      </div>
      {isCommitOverlayOpen && (
        <PortalPopup
          overlayColor="rgba(0, 0, 0, 0.5)"
          placement="Centered"
          onOutsideClick={closeCommitOverlay}
        >
          <CommitOverlay onClose={closeCommitOverlay} />
        </PortalPopup>
      )}
    </>
  );
};

export default CommitsSet;
