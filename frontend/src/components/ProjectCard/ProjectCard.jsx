import { useCallback, useId, useState } from "react";
import { Link } from "react-router-dom";
import DetailsButton from "../DetailsButton/DetailsButton.jsx";
import LoadingDots from "../LoadingDots/LoadingDots.jsx";
import { formatDate } from "../../utils/format.js";
import styles from "./ProjectCard.module.css";

const ProjectCard = ({ project }) => {
  const [open, setOpen] = useState(false);
  const [imageStatus, setImageStatus] = useState("loading"); // "loading" | "loaded" | "error"
  const detailsId = useId();

  // covers images that finished loading before React attached onLoad (cache)
  const imgRef = useCallback((img) => {
    if (img?.complete && img.naturalWidth > 0) setImageStatus("loaded");
  }, []);

  return (
    <article className={styles.card}>
      <div className={styles.text}>
        <h2 className={styles.name}>{project.name}</h2>
        <p className={styles.meta}>Last modified: {formatDate(project.lastModified)}</p>
        <p className={styles.meta}># of Commits: {project.commitCount}</p>
      </div>

      {imageStatus === "loading" && (
        <div className={styles.loadingSlot}>
          <div className={styles.loadingBox}>
            <LoadingDots label={`Loading preview of ${project.name}`} />
          </div>
        </div>
      )}
      {imageStatus === "error" && (
        <div className={`${styles.frame} ${styles.fallback}`}>Preview unavailable</div>
      )}

      {/* stays in the DOM while loading so the browser fetches it */}
      <Link
        to={`/projects/${project.id}/timeline`}
        className={styles.frameLink}
        aria-label={`Open ${project.name}`}
        hidden={imageStatus !== "loaded"}
      >
        <span className={styles.frame}>
          <img
            ref={imgRef}
            src={project.thumbnail}
            alt=""
            onLoad={() => setImageStatus("loaded")}
            onError={() => setImageStatus("error")}
          />
        </span>
      </Link>

      <div className={styles.details}>
        <DetailsButton expanded={open} controls={detailsId} onClick={() => setOpen((o) => !o)} />
        {open && (
          <p id={detailsId} className={styles.description}>
            {project.description || "The description wasn’t added."}
          </p>
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
