import { useCallback } from "react";
import styles from "./Header.module.css";

const Header = () => {
  const onInfoIconClick = useCallback(() => {
    // TO-DO
  }, []);

  return (
    // Header container
    <div className={styles.header}>
      {/* GitGallery logo container */}
      <div className={styles.gitgalleryLogo} onClick={onInfoIconClick}>
        {/* GitGallery logo vector*/}
        <img className={styles.vectorIcon} alt="" />
        {/* GitGallery logo text */}
        <img className={styles.textIcon} alt="" />
      </div>

      {/* Info icon */}
      <img className={styles.infoIcon} alt="" onClick={onInfoIconClick} />
    </div>
  );
};

export default Header;
