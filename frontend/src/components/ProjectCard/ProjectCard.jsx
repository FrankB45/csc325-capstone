import { useId, useState } from "react";
import { Link } from "react-router-dom";
import { formatDate } from "../../utils/format.js";
import styles from "./ProjectCard.module.css";

const ProjectCard = ({ project }) => {
  const [open, setOpen] = useState(false);
  const detailsId = useId();

  return (
    <article className={styles.card}>
      <Link to={`/projects/${project.id}`} className={styles.thumbLink}>
        <img
          className={styles.thumb}
          src={project.thumbnail}
          alt={`Latest screenshot of ${project.name}`}
        />
      </Link>

      <div className={styles.body}>
        <h2 className={styles.name}>{project.name}</h2>
        <p className={styles.meta}>Last modified: {formatDate(project.lastModified)}</p>
        <p className={styles.meta}>Commits#: {project.commitCount}</p>

        <button
          type="button"
          className={styles.detailsToggle}
          aria-expanded={open}
          aria-controls={detailsId}
          onClick={() => setOpen((o) => !o)}
        >
          Details <span aria-hidden="true" className={open ? styles.chevronOpen : ""}>▾</span>
        </button>

        {open && (
          <p id={detailsId} className={styles.details}>
            {project.description || "The description wasn’t added."}
          </p>
        )}
      </div>
    </article>
  );
};

export const ProjectCardSkeleton = () => (
  <div className={`${styles.card} ${styles.skeleton}`} aria-hidden="true">
    <div className={styles.thumb} />
    <div className={styles.body} />
  </div>
);

export default ProjectCard;
