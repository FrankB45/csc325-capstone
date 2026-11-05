import PageLayout from "../components/PageLayout/PageLayout.jsx";
import Button from "../components/NewProjectButton/NewProjectButton.jsx";
import ProjectCard, { ProjectCardSkeleton } from "../components/ProjectCard/ProjectCard.jsx";
import { useProjects } from "../hooks/useProjects.js";
import styles from "./Gallery.module.css";

const Gallery = () => {
  const { projects, isLoading, error } = useProjects();

  return (
    <PageLayout width="wide">
      <div className={styles.top}>
        <h1 className={styles.title}>Gallery</h1>
        <NewProjectButton to="/new-project" size="sm">New Project</NewProjectButton>
      </div>

      {error && <p role="alert" className={styles.error}>{error}</p>}

      <div className={styles.grid} aria-busy={isLoading}>
        {isLoading
          ? Array.from({ length: 3 }, (_, i) => <ProjectCardSkeleton key={i} />)
          : projects.map((p) => <ProjectCard key={p.id} project={p} />)}
      </div>

      {!isLoading && !error && projects.length === 0 && (
        <p className={styles.empty}>No projects yet. Create your first one to see its timeline here.</p>
      )}
    </PageLayout>
  );
};

export default Gallery;
