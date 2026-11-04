import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./NewProjectButton.module.css";

const NewProjectButton = () => {
  const navigate = useNavigate();
  const onNewProjectButtonClick = useCallback(() => {
    navigate("/new-project");
  }, [navigate]);

  return (
    <button
      className={styles.newProjectButton}
      type="button"
      onClick={onNewProjectButtonClick}
    >
      <b className={styles.newProjectText}>New Project</b>
    </button>
  );
};

export default NewProjectButton;
