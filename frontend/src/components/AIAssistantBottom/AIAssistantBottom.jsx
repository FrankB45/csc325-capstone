import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./AIAssistantBottom.module.css";

const NewProjectButton = () => {

  return (
    <button
      className={styles.AIAssistantBottomButton}
      type="button"
      onClick={onNewProjectButtonClick}
    >
      <b className={styles.newProjectText}>Send</b>
    </button>
  );
};

export default NewProjectButton;
