import AddCommitButton from "../AddCommitButton/AddCommitButton.jsx";
import styles from "./EmptyCommitSlot.module.css";

/** Empty second slot in Compare mode. */
const EmptyCommitSlot = ({ isPicking, onAdd }) => (
  <div className={styles.slot}>
    {isPicking ? (
      <p className={styles.hint}>Select a commit on the timeline below</p>
    ) : (
      <AddCommitButton onClick={onAdd} />
    )}
  </div>
);

export default EmptyCommitSlot;
