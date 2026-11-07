import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import closeIcon from "../../assets/aabb99a6001b38cd14e74760561137277bcfd761.png";
import styles from "./CommitOverlay.module.css";

/** Full-size screenshot on a white overlay with an orange × in the corner. Closes on Esc, ×, or backdrop click. */
const CommitOverlay = ({ commit, onClose }) => {
  const closeRef = useRef(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    const onKeyDown = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [onClose]);

  return createPortal(
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-label={`Screenshot at commit ${commit.sha.slice(0, 7)}: ${commit.message}`}
      onClick={onClose}
    >
      <button ref={closeRef} type="button" className={styles.close} onClick={onClose} aria-label="Close">
        <img src={closeIcon} alt="" />
      </button>
      <div className={styles.frame} onClick={(e) => e.stopPropagation()}>
        <img src={commit.image} alt={`Full screenshot at commit ${commit.sha.slice(0, 7)}: ${commit.message}`} />
      </div>
    </div>,
    document.body,
  );
};

export default CommitOverlay;
