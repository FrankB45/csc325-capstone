import Header from "../Header/Header.jsx";
import styles from "./PageLayout.module.css";

/** Header + <main>. `width` is "narrow" (forms), "wide" (gallery/timeline) or "full" (landing). */
const PageLayout = ({ width = "wide", children }) => (
  <div className={styles.page}>
    <Header />
    <main className={`${styles.main} ${styles[width]}`}>{children}</main>
  </div>
);

export default PageLayout;
