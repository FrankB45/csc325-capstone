import { Link } from "react-router-dom";
import styles from "./CancelButton.module.css";

/** Light text-only "Cancel". Pass `to` to navigate, or `onClick` for an action. `disabled` only applies to the button form. */
const CancelButton = ({ to, onClick, disabled = false, children = "Cancel" }) =>
  to ? (
    <Link to={to} className={styles.cancel}>{children}</Link>
  ) : (
    <button type="button" className={styles.cancel} onClick={onClick} disabled={disabled}>{children}</button>
  );

export default CancelButton;
