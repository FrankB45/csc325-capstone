import { useEffect, useState } from "react";
import { MOCK_PROJECTS } from "../data/mock.js";

/**
 * Gallery data. Currently resolves mock data after a short delay so the
 * loading state is visible.
 * TODO: replace the timeout with fetch("/api/projects/") once the endpoint exists.
 */
export function useProjects() {
  const [state, setState] = useState({ projects: [], isLoading: true, error: "" });

  useEffect(() => {
    const timer = setTimeout(
      () => setState({ projects: MOCK_PROJECTS, isLoading: false, error: "" }),
      500,
    );
    return () => clearTimeout(timer);
  }, []);

  return state;
}
