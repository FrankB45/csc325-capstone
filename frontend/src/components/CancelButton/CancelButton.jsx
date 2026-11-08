import { Link } from "react-router-dom";
import styles from "./CancelButton.module.css";

/** Light text-only "Cancel". Pass `to` to navigate, or `onClick` for an action. */
const CancelButton = ({ to, onClick, children = "Cancel" }) =>
  to ? (
    <Link to={to} className={styles.cancel}>{children}</Link>
  ) : (
    <button type="button" className={styles.cancel} onClick={onClick}>{children}</button>
  );

export default CancelButton;
