import styles from "./CommitPreview.module.css";

const CommitPreview = ({ commit, onOpen }) => {
  if (!commit.image) {
    return (
      <div className={styles.frame}>
        <p>
          {commit.status === "failed"
            ? "Capture failed"
            : "Screenshot is not ready yet"}
        </p>

        {commit.error_message && <p>{commit.error_message}</p>}
      </div>
    );
  }

  return (
    <button
      type="button"
      className={styles.frame}
      onClick={() => onOpen(commit)}
      aria-label={`View screenshot at commit ${commit.sha.slice(0, 7)}`}
    >
      <img
        src={commit.image}
        alt={`Screenshot for ${commit.message}`}
      />
    </button>
  );
};

export default CommitPreview;