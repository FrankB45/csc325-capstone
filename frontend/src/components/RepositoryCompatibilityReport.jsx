export default function RepositoryCompatibilityReport({ report }) {
    if (!report) return null;

    let statusMessage;
    let announcementRole = "status";
    if (report.overall_status === "rejected") {
        statusMessage = "Repository rejected by the implemented checks.";
        announcementRole = "alert";
    } else if (report.overall_status === "unavailable") {
        statusMessage = "Compatibility checking could not finish.";
        announcementRole = "alert";
    } else {
        statusMessage = "Compatibility checking is pending.";
    }

    return (
        <section aria-label="Repository compatibility" role={announcementRole}>
            <p>{statusMessage}</p>
            <p>{report.reason}</p>
            <p>History ({report.history.history_status}): {report.history.reason}</p>
            <p>HTML pages ({report.html.html_status}): {report.html.reason}</p>
            <p>Dependency checking is pending. {report.dependencies.reason}</p>
            <p>Project setup is unavailable.</p>
        </section>
    );
}
