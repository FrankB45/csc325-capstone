import { useEffect, useState } from "react";

import Header from "../components/Header/Header.jsx";
import RepositoryValidation from "../components/RepositoryValidation.jsx";

function Home() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showSubmission, setShowSubmission] = useState(false);
  const [refreshCount, setRefreshCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadProjects() {
      setLoading(true);
      setError("");

      try {
        const response = await fetch("/api/projects/", {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Could not load the project gallery.");
        }

        const data = await response.json();
        setProjects(data.projects);
      } catch (loadError) {
        if (loadError.name !== "AbortError") {
          setError(loadError.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadProjects();

    return () => controller.abort();
  }, [refreshCount]);

  function handleProjectCreated() {
    setShowSubmission(false);
    setRefreshCount((count) => count + 1);
  }

  return (
    <>
      <Header />

      <main className="gallery-page">
        {showSubmission ? (
          <>
            <button type="button" onClick={() => setShowSubmission(false)}>
              Back to gallery
            </button>

            <RepositoryValidation
              onProjectCreated={handleProjectCreated}
            />
          </>
        ) : (
          <>
            <h1>Shared Project Gallery</h1>

            <button type="button" onClick={() => setShowSubmission(true)}>
              New Project
            </button>

            {loading && <p>Loading projects…</p>}
            {error && <p role="alert">{error}</p>}

            {!loading && !error && projects.length === 0 && (
              <p>No projects are available yet. Add a project to get started.</p>
            )}

            {!loading && !error && projects.length > 0 && (
              <ul>
                {projects.map((project) => (
                  <li key={project.id}>
                    <h2>{project.project_name}</h2>
                    <p>
                      {project.repository_owner}/{project.repository_name}
                    </p>
                    <p>
                      {project.latest_job
                        ? `Status: ${project.latest_job.status}`
                        : "No analysis yet"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </main>
    </>
  );
}

export default Home;