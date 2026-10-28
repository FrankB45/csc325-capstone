import { useState } from "react"

export default function RepositoryValidation() {
    const [url, setUrl] = useState("")
    const [repository, setRepository] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState("")

    async function handleSubmit(event) {
        event.preventDefault();

        if (isLoading) return;

        setError("");
        setRepository(null);

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
        } catch (error) {
            setError(error.message || "Something went wrong. Try again.");
        } finally {
            setIsLoading(false);
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
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://github.com/owner/repository"
                disabled={isLoading}
                spellCheck={false}
                />

                <button type="submit" disabled={isLoading}>
                {isLoading ? "Loading…" : "Load repository"}
                </button>
            </form>

            {isLoading && <p role="status">Looking up the repository…</p>}

            {error && <p role="alert">{error}</p>}

            {repository && (
                <section aria-label="Repository details">
                <h2>{repository.full_name}</h2>
                <p>{repository.description || "No description provided."}</p>
                <p>Default branch: {repository.default_branch}</p>
                </section>
            )}
        </div>
    )
}