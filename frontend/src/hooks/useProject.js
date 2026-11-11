import { useEffect, useState } from "react";

export function useProject(projectId) {
  const [project, setProject] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let timer;

    async function loadProject() {
      try {
        const response = await fetch(`/api/projects/${projectId}/`, {
          signal: controller.signal,
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error || data.detail || "Could not load the project."
          );
        }

        if (controller.signal.aborted) return;

        setProject(data);
        setError("");

        if (["queued", "processing"].includes(data.analysis?.status)) {
          timer = setTimeout(loadProject, 2000);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        setError(err.message || "Could not load the project.");
      }
    }

    loadProject();

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [projectId]);

  return {
    project,
    error,
    isLoading: project === null && error === "",
  };
}