import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./Header.module.css";
import logoIcon from "../../assets/GitGallery Logo.svg";
import infoIcon from "../../assets/Info Icon.svg";

const Header = () => {
  const navigate = useNavigate();
  const onInfoIconClick = useCallback(() => {
    navigate("/info");
  }, [navigate]);

  return (
    // Header container
    <header className={styles.header}>
      {/* GitGallery logo vector*/}
      <img
        className={styles.gitgalleryLogo}
        alt="GitGallery Logo Icon"
        src={logoIcon}
      />

      {/* Info icon */}
      <img
        className={styles.infoIcon}
        alt="Info"
        src={infoIcon}
        onClick={onInfoIconClick}
      />
    </header>
  );
};

export default Header;
