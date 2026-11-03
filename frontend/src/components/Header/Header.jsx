import { useCallback } from "react";
import styles from "./Header.module.css";

const Header = () => {
  const onInfoIconClick = useCallback(() => {
    // Add your code here
  }, []);

  return (
    <div className={styles.header}>
      <img className={styles.infoIcon} alt="" onClick={onInfoIconClick} />
      <div className={styles.gitgalleryLogo} onClick={onInfoIconClick}>
        <img className={styles.textIcon} alt="" />
        <img className={styles.vectorIcon} alt="" />
      </div>
    </div>
  );
};

export default Header;
