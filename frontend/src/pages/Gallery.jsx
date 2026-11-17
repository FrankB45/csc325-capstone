import { useCallback, useState } from "react";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import NewProjectButton from "../components/New Project Button/NewProjectButton.jsx";
import ProjectCard, { ProjectCardSkeleton } from "../components/ProjectCard/ProjectCard.jsx";
import Pager from "../components/Pager/Pager.jsx";
import Modal from "../components/Modal/Modal.jsx";
import CancelButton from "../components/CancelButton/CancelButton.jsx";
import { useProjects } from "../hooks/useProjects.js";
import styles from "./Gallery.module.css";

const PAGE_SIZE = 3;

const Gallery = () => {
  const { projects, isLoading, error, removeProject } = useProjects();
  const [page, setPage] = useState(0);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const pageCount = Math.ceil(projects.length / PAGE_SIZE);
  const currentPage = Math.min(page, Math.max(pageCount - 1, 0));
  const visible = projects.slice(
    currentPage * PAGE_SIZE,
    currentPage * PAGE_SIZE + PAGE_SIZE,
  );

  const closeDialog = useCallback(() => {
    setPendingDelete(null);
    setDeleteError("");
  }, []);

  async function confirmDelete() {
    setIsDeleting(true);
    setDeleteError("");
    try {
      await removeProject(pendingDelete.id);
      setPage((current) =>
        Math.min(
          current,
          Math.max(Math.ceil((projects.length - 1) / PAGE_SIZE) - 1, 0),
        ),
      );
      setPendingDelete(null);
    } catch (err) {
      setDeleteError(err.message || "Could not delete the project.");
    } finally {
      setIsDeleting(false);
    }
  }

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
          {visible.map((p) => (
            <ProjectCard key={p.id} project={p} onDelete={setPendingDelete} />
          ))}
        </div>
      )}

      {pageCount > 1 && <Pager pageCount={pageCount} page={currentPage} onChange={setPage} />}

      {pendingDelete && (
        <Modal title="Delete project" onClose={closeDialog}>
          <section className={styles.confirm}>
            <h2>Delete “{pendingDelete.name}”?</h2>
            <p>This removes the project and all of its screenshots. It can’t be undone.</p>
            {deleteError && <p role="alert" className={styles.error}>{deleteError}</p>}
            <div className={styles.confirmActions}>
              <CancelButton onClick={closeDialog} />
              <button
                type="button"
                className={styles.confirmDelete}
                onClick={confirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </section>
        </Modal>
      )}
    </PageLayout>
  );
};

export default Gallery;