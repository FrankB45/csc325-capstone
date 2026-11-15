import styles from "./CommitPreview.module.css";

const getDisplayErrorMessage = (errorMessage, selectedPage) => {
  if (!errorMessage || !selectedPage) return errorMessage;

  const pageMatch = errorMessage.match(/"([^"]+)"/);
  if (!pageMatch || pageMatch[1] === selectedPage) return errorMessage;

  return errorMessage.replace(pageMatch[1], selectedPage);
};

const CommitPreview = ({ commit, onOpen, selectedPage }) => {
  const displayError = getDisplayErrorMessage(commit.error_message, selectedPage);

  if (!commit.image) {
    return (
      <div className={styles.frame}>
        <p>
          {commit.status === "failed"
            ? "Capture failed"
            : "Screenshot is not ready yet"}
        </p>

        {displayError && <p>{displayError}</p>}
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