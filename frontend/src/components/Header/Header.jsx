import { useCallback } from "react";
import styles from "./Header.module.css";
import logoIcon from "../../assets/GitGallery Logo.svg";
import infoIcon from "../../assets/Info Icon.svg";

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
        <img
          className={styles.vectorIcon}
          alt="GitGallery Logo Icon"
          src={logoIcon}
        />
      </div>

      {/* Info icon */}
      <img
        className={styles.infoIcon}
        alt="Info"
        src={infoIcon}
        onClick={onInfoIconClick}
      />
    </div>
  );
};

export default Header;
