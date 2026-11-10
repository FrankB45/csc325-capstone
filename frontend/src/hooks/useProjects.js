import { useEffect, useState } from "react";

export function useProjects() {
  const [state, setState] = useState({
    projects: [],
    isLoading: true,
    error: "",
  });

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

        if (
          projects.some((project) =>
            ["queued", "processing"].includes(project.status)
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

  return state;
}