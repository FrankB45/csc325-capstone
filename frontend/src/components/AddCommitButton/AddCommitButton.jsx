import styles from "./AddCommitButton.module.css";

/** Coral "Add Commit" pill shown in the empty Compare slot. */
const AddCommitButton = ({ onClick, children = "Add Commit" }) => (
  <button type="button" className={styles.button} onClick={onClick}>
    {children}
  </button>
);

export default AddCommitButton;
