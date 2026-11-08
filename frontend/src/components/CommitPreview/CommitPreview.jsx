import styles from "./CommitPreview.module.css";

/** Gradient-framed screenshot of a commit; click to open the full-size overlay. */
const CommitPreview = ({ commit, onOpen }) => (
  <button
    type="button"
    className={styles.frame}
    onClick={() => onOpen(commit)}
    aria-label={`View full screenshot at commit ${commit.sha.slice(0, 7)}: ${commit.message}`}
  >
    <img src={commit.image} alt="" />
  </button>
);

export default CommitPreview;
