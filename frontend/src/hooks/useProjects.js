import { useEffect, useState, useCallback } from "react";
import { isUpdateInProgress } from "../utils/updateAttempt.js";

export function useProjects() {
  const [state, setState] = useState({
    projects: [],
    isLoading: true,
    error: "",
  });

  const removeProject = useCallback(async (id) => {
    const response = await fetch(`/api/projects/${id}/`, { method: "DELETE" });

    // 404 means it's already gone, so just drop it from the list.
    if (!response.ok && response.status !== 404) {
      let data = {};
      try {
        data = await response.json();
      } catch {
        /* no body */
      }
      throw new Error(data.error || "Could not delete the project.");
    }

    setState((previous) => ({
      ...previous,
      projects: previous.projects.filter((project) => project.id !== id),
    }));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer;

    async function loadProjects() {
      try {
        const response = await fetch("/api/projects/", {
          signal: controller.signal,
        });
        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error || data.detail || "Could not load projects."
          );
        }

        if (controller.signal.aborted) return;

        const projects = data.projects.map((project) => ({
          ...project,
          lastModified: project.updated_at,
          commitCount: project.progress.total,
          thumbnail: project.thumbnail_url,
        }));

        setState({
          projects,
          isLoading: false,
          error: "",
        });

        // A card's own status describes the displayed analysis, so also watch
        // for a newer update that is still being processed.
        if (
          projects.some(
            (project) =>
              ["queued", "processing"].includes(project.status) ||
              isUpdateInProgress(project.update_attempt)
          )
        ) {
          timer = setTimeout(loadProjects, 2000);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        setState((previous) => ({
          ...previous,
          isLoading: false,
          error: err.message || "Could not load projects.",
        }));
      }
    }

    loadProjects();

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, []);

  return { ...state, removeProject };
}