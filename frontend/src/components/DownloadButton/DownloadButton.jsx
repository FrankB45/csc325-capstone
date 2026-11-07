import styles from "./DownloadButton.module.css";

/** Icon-only download button (amber tray + arrow). */
const DownloadButton = ({ label = "Download", onClick, disabled = false }) => (
  <button type="button" className={styles.button} aria-label={label} title={label} onClick={onClick} disabled={disabled}>
    <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3.5v11" />
      <path d="M7.5 10.5l4.5 4.5 4.5-4.5" />
      <path d="M4.5 15.5v4h15v-4" />
    </svg>
  </button>
);

export default DownloadButton;
