import { useState } from "react"
import RepositoryCompatibilityReport from "./RepositoryCompatibilityReport"

export default function RepositoryValidation() {
    const [url, setUrl] = useState("")
    const [repository, setRepository] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState("")
    const [compatibilityReport, setCompatibilityReport] = useState(null)

    async function handleSubmit(event) {
        event.preventDefault();

        if (isLoading) return;

        setError("");
        setRepository(null);
        setCompatibilityReport(null);

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

            let compatibilityResponse;
            try {
                compatibilityResponse = await fetch("/api/repo/compatibility/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    body: JSON.stringify({ url: url.trim() }),
                });
                const report = await compatibilityResponse.json();
                const checkStatuses = ["passed", "rejected", "unavailable"];

                if (!report || typeof report !== "object") {
                    setError("The compatibility service returned an unexpected response. Try again.");
                } else if (typeof report.error === "string" && report.error.trim()) {
                    setError(report.error);
                } else if (typeof report.detail === "string" && report.detail.trim()) {
                    setError(report.detail);
                } else if (
                    !["rejected", "unavailable", "pending"].includes(report.overall_status) ||
                    typeof report.reason !== "string" ||
                    !report.history ||
                    !checkStatuses.includes(report.history.history_status) ||
                    typeof report.history.reason !== "string" ||
                    !report.html ||
                    !checkStatuses.includes(report.html.html_status) ||
                    typeof report.html.reason !== "string" ||
                    !report.dependencies ||
                    report.dependencies.status !== "pending" ||
                    typeof report.dependencies.reason !== "string" ||
                    report.setup_available !== false ||
                    report.same_snapshot_guaranteed !== false
                ) {
                    setError("The compatibility service returned an unexpected report. Try again.");
                } else if (
                    (compatibilityResponse.status === 200 && report.overall_status !== "unavailable") ||
                    (compatibilityResponse.status === 502 && report.overall_status === "unavailable")
                ) {
                    // A useful unavailable report arrives with HTTP 502.
                    setCompatibilityReport(report);
                } else {
                    setError("The compatibility service returned an unexpected response. Try again.");
                }
            } catch {
                if (compatibilityResponse) {
                    setError("The compatibility service returned an unreadable response. Try again.");
                } else {
                    setError("Could not reach the compatibility service. Try again.");
                }
            }
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
            <RepositoryCompatibilityReport report={compatibilityReport} />
        </div>
    )
}