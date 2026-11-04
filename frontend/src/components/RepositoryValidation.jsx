import { useState } from "react"
import RepositoryCompatibilityReport from "./RepositoryCompatibilityReport"

export default function RepositoryValidation({ onProjectCreated }) {
    const [url, setUrl] = useState("")
    const [repository, setRepository] = useState(null)
    const [projectName, setProjectName] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [error, setError] = useState("")
    const [compatibilityReport, setCompatibilityReport] = useState(null)

    async function handleSubmit(event) {
        event.preventDefault();

        if (isLoading || isSaving) return;

        setError("");
        setRepository(null);
        setProjectName("");

        if (!url.trim()) {
            setError("Enter a repository URL.");
            return;
        }

        setIsLoading(true);

        try {
            const response = await fetch("/api/repo/info/", {
                method: "POST",
                headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
                },
                body: JSON.stringify({ url: url.trim() }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                data.error || data.detail || "Could not load the repository."
                );
            }

            setRepository(data);
            setProjectName(data.name);
        } catch (error) {
            setError(error.message || "Something went wrong. Try again.");
        } finally {
            setIsLoading(false);
    }
  }

    async function handleAddProject(event) {
        event.preventDefault()
        if (!repository || isSaving) return

        setError("")
        setIsSaving(true)

        try {
            const response = await fetch("/api/projects/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({
                    project_name: projectName,
                    repository_owner: repository.owner,
                    repository_name: repository.name,
                    repository_url: repository.url,
                    analysis_status: "not_started",
                }),
            })
            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.error || "Could not add the project to the gallery.")
            }

            onProjectCreated(data)
        } catch (saveError) {
            setError(saveError.message || "Could not add the project to the gallery.")
        } finally {
            setIsSaving(false)
        }
    }

    return (
        <div>
            <form onSubmit={handleSubmit}>
                <label htmlFor="repository-url">GitHub repository URL</label>

                <input
                id="repository-url"
                type="text"
                value={url}
                onChange={(event) => {
                    setUrl(event.target.value)
                    setRepository(null)
                    setProjectName("")
                    setError("")
                }}
                placeholder="https://github.com/owner/repository"
                disabled={isLoading || isSaving}
                spellCheck={false}
                />

                <button type="submit" disabled={isLoading || isSaving}>
                {isLoading ? "Loading…" : "Load repository"}
                </button>
            </form>

            {isLoading && <p role="status">Looking up the repository…</p>}
            {isSaving && <p role="status">Adding the project to the shared gallery…</p>}

            {error && <p role="alert">{error}</p>}

            {repository && (
                <section aria-label="Repository details">
                <p role="status">Repository found and publicly accessible.</p>
                <h2>{repository.full_name}</h2>
                <p>{repository.description || "No description provided."}</p>
                <p>Default branch: {repository.default_branch}</p>
                <form onSubmit={handleAddProject}>
                    <label htmlFor="project-name">Project name</label>
                    <input
                        id="project-name"
                        type="text"
                        value={projectName}
                        onChange={(event) => setProjectName(event.target.value)}
                        maxLength={200}
                        required
                        disabled={isSaving}
                    />
                    <button
                        className="button button--primary"
                        type="submit"
                        disabled={isSaving || !projectName.trim()}
                    >
                        {isSaving ? "Adding…" : "Add to shared gallery"}
                    </button>
                </form>
                </section>
            )}
            <RepositoryCompatibilityReport report={compatibilityReport} />
        </div>
    )
}