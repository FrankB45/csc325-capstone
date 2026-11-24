import { useId, useState } from "react";
import { Link } from "react-router-dom";
import DetailsButton from "../DetailsButton/DetailsButton.jsx";
import LoadingDots from "../LoadingDots/LoadingDots.jsx";
import trashCanIcon from "../../assets/trash-can.svg";
import { formatDate } from "../../utils/format.js";
import {
  describeUpdateProgress,
  isCandidateAttempt,
  isUpdateInProgress,
} from "../../utils/updateAttempt.js";
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

const ProjectCard = ({ project, onDelete }) => {
  const [open, setOpen] = useState(false);
  const detailsId = useId();
  const repository = project.repository_owner && project.repository_name
    ? `${project.repository_owner}/${project.repository_name}`
    : null;

  return (
    <article className={styles.card}>
      <div className={styles.text}>
        <div className={styles.headingRow}>
          <h2 className={`${styles.name} ${styles.truncate}`} title={project.name}>
            {project.name}
          </h2>
          {onDelete && (
            <button
              type="button"
              className={styles.delete}
              onClick={() => onDelete(project)}
              aria-label={`Delete ${project.name}`}
            >
              <img
                src={trashCanIcon}
                alt=""
                className={styles.deleteIcon}
                aria-hidden="true"
              />
            </button>
          )}
        </div>
        {repository && (
          <p className={`${styles.meta} ${styles.truncate}`} title={repository}>
            {repository}
          </p>
        )}
        <p className={styles.meta}>Last modified: {formatDate(project.lastModified)}</p>
        <p className={styles.meta}># of Commits: {project.commitCount}</p>
        <p className={styles.meta}>
          Status: {project.status ? project.status.replaceAll("_", " ") : "No analysis yet"}
        </p>
        <p className={styles.meta}>
          {project.progress.processed} / {project.progress.total} processed
          {" · "}
          {project.progress.failed} failed
        </p>
        {/* The values above describe the displayed analysis; a newer update is shown separately. */}
        {isUpdateInProgress(project.update_attempt) && (
          <p className={styles.meta}>
            {describeUpdateProgress(project.update_attempt)} · showing previous results
          </p>
        )}
        {isCandidateAttempt(project.job_id, project.update_attempt) &&
          !isUpdateInProgress(project.update_attempt) && (
            <p className={styles.meta}>Latest update did not replace these results.</p>
          )}
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

export default ProjectCard;
