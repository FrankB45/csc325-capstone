import { useCallback, useEffect, useState } from "react";
import { isUpdateInProgress } from "../utils/updateAttempt.js";

export function useProject(projectId) {
  const [project, setProject] = useState(null);
  const [error, setError] = useState("");
  // Changing this number makes the effect below load the project again right away.
  const [refreshCount, setRefreshCount] = useState(0);

  const refresh = useCallback(() => setRefreshCount((count) => count + 1), []);

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

        // Keep polling while the displayed analysis or a newer update attempt is
        // still being processed. The displayed analysis may already be complete.
        const analysisRunning = ["queued", "processing"].includes(data.analysis?.status);
        if (analysisRunning || isUpdateInProgress(data.update_attempt)) {
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
  }, [projectId, refreshCount]);

  return {
    project,
    error,
    isLoading: project === null && error === "",
    refresh,
  };
}
