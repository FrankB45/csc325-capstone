import styles from "./SyncButton.module.css";

/**
 * Coral "Sync Updates" button; the icon spins while `syncing` (work is in progress).
 * `paused` also disables the button, but without spinning or marking it busy,
 * for when nothing is loading and the user should wait or check first.
 */
const SyncButton = ({ syncing = false, paused = false, onClick, children = "Sync Updates" }) => (
  <button
    type="button"
    className={styles.button}
    onClick={onClick}
    disabled={syncing || paused}
    aria-busy={syncing || undefined}
  >
    {children}
    <svg className={`${styles.icon} ${syncing ? styles.spinning : ""}`} viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true">
      <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z" />
    </svg>
  </button>
);

export default SyncButton;
