import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./ViewGalleryButton.module.css";

const ViewGalleryButton = () => {
  const navigate = useNavigate();
  const onViewGalleryButtonClick = useCallback(() => {
    navigate("/gallery");
  }, [navigate]);

  return (
    <button
      className={styles.viewGalleryButton}
      type="button"
      onClick={onViewGalleryButtonClick}
    >
      <b className={styles.viewGalleryText}>View Gallery</b>
    </button>
  );
};

export default ViewGalleryButton;
