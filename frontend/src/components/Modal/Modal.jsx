import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import closeIcon from "../../assets/aabb99a6001b38cd14e74760561137277bcfd761.png";
import styles from "./Modal.module.css";

const Modal = ({ title, onClose, children }) => {
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
    <div className={styles.backdrop} onClick={onClose}>
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <button ref={closeRef} type="button" className={styles.close} onClick={onClose} aria-label="Close">
          <img src={closeIcon} alt="" />
        </button>
        {children}
      </div>
    </div>,
    document.body,
  );
};

export default Modal;
