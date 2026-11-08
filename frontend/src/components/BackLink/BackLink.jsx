import { Link } from "react-router-dom";
import styles from "./BackLink.module.css";

/** "< Back to Gallery" style link. */
const BackLink = ({ to, children }) => (
  <Link to={to} className={styles.link}>
    <span aria-hidden="true">&lt; </span>
    {children}
  </Link>
);

export default BackLink;
