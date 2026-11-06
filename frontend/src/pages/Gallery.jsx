import { useState } from "react";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import NewProjectButton from "../components/New Project Button/NewProjectButton.jsx";
import ProjectCard, { ProjectCardSkeleton } from "../components/ProjectCard/ProjectCard.jsx";
import Pager from "../components/Pager/Pager.jsx";
import { useProjects } from "../hooks/useProjects.js";
import styles from "./Gallery.module.css";

const PAGE_SIZE = 3;

const Gallery = () => {
  const { projects, isLoading, error } = useProjects();
  const [page, setPage] = useState(0);

  const pageCount = Math.ceil(projects.length / PAGE_SIZE);
  const visible = projects.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  return (
    <PageLayout width="gallery">
      <div className={styles.top}>
        <h1 className={styles.title}>Gallery</h1>
        <NewProjectButton />
      </div>

      {error && <p role="alert" className={styles.error}>{error}</p>}

      {isLoading && (
        <div className={styles.grid} aria-busy="true">
          {Array.from({ length: PAGE_SIZE }, (_, i) => <ProjectCardSkeleton key={i} />)}
        </div>
      )}

      {!isLoading && !error && projects.length === 0 && (
        <p className={styles.empty}>You don’t have any projects added to Gallery yet.</p>
      )}

      {!isLoading && visible.length > 0 && (
        <div className={styles.grid}>
          {visible.map((p) => <ProjectCard key={p.id} project={p} />)}
        </div>
      )}

      {pageCount > 1 && <Pager pageCount={pageCount} page={page} onChange={setPage} />}
    </PageLayout>
  );
};

export default Gallery;
