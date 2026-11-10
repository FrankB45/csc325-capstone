import { useId, useState } from "react";
import { Link } from "react-router-dom";
import DetailsButton from "../DetailsButton/DetailsButton.jsx";
import LoadingDots from "../LoadingDots/LoadingDots.jsx";
import { formatDate } from "../../utils/format.js";
import styles from "./ProjectCard.module.css";

const ProjectThumbnail = ({ url }) => {
  const [failed, setFailed] = useState(false);

  if (!url || failed) {
    return (
      <span className={styles.frame + " " + styles.fallback}>
        Preview unavailable — open project
      </span>
    );
  }

  return (
    <span className={styles.frame}>
      <img
        src={url}
        alt=""
        onError={() => setFailed(true)}
      />
    </span>
  );
};

const ProjectCard = ({ project }) => {
  const [open, setOpen] = useState(false);
  const detailsId = useId();

  return (
    <article className={styles.card}>
      <div className={styles.text}>
        <h2 className={styles.name}>{project.name}</h2>
        <p className={styles.meta}>Last modified: {formatDate(project.lastModified)}</p>
        <p className={styles.meta}># of Commits: {project.commitCount}</p>
        <p className={styles.meta}>
          Status: {project.status.replaceAll("_", " ")}
        </p>
        <p className={styles.meta}>
          {project.progress.processed} / {project.progress.total} processed
          {" · "}
          {project.progress.failed} failed
        </p>
      </div>

      <Link
        to={`/projects/${project.id}/timeline`}
        className={styles.frameLink}
        aria-label={`Open ${project.name}`}
      >
        <ProjectThumbnail
          key={project.thumbnail || "no-thumbnail"}
          url={project.thumbnail}
        />
      </Link>

      <div className={styles.details}>
        <DetailsButton expanded={open} controls={detailsId} onClick={() => setOpen((o) => !o)} />
        {open && (
          <div id={detailsId} className={styles.description}>
            <a
              href={project.repository_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {project.repository_url}
            </a>

            {project.page_path && (
              <p>
                Page: <code>{project.page_path}</code>
              </p>
            )}
          </div>
        )}
      </div>
    </article>
  );
};

/** Placeholder card while the project list itself is loading. */
export const ProjectCardSkeleton = () => (
  <div className={styles.card} aria-hidden="true">
    <div className={styles.text}>
      <div className={`${styles.bar} ${styles.barName}`} />
      <div className={`${styles.bar} ${styles.barMeta}`} />
      <div className={`${styles.bar} ${styles.barMeta}`} />
    </div>
    <div className={styles.loadingSlot}>
      <div className={styles.loadingBox}>
        <LoadingDots />
      </div>
    </div>
  </div>
);

export default ProjectCard;
