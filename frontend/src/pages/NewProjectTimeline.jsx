import { useState } from "react";
import { useProject } from "../hooks/useProject.js";
import { Link, useParams } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import BackLink from "../components/BackLink/BackLink.jsx";
import DownloadButton from "../components/DownloadButton/DownloadButton.jsx";
import ModeToggle from "../components/ModeToggle/ModeToggle.jsx";
import CommitPreview from "../components/CommitPreview/CommitPreview.jsx";
import EmptyCommitSlot from "../components/EmptyCommitSlot/EmptyCommitSlot.jsx";
import Timeline from "../components/Timeline/Timeline.jsx";
import CommitOverlay from "../components/CommitOverlay/CommitOverlay.jsx";
import AIAssistant from "../components/AIAssistant/AIAssistant.jsx";
import styles from "./ProjectTimeline.module.css";

const ProjectTimelineView = ({ project, commits }) => {
  const analysis = project.analysis;
  const [mode, setMode] = useState("standard"); // "standard" | "compare"
  const [picks, setPicks] = useState(() => {
    const latestCaptured = commits.filter((commit) => commit.image).at(-1);

    return latestCaptured
      ? [latestCaptured.id]
      : commits.slice(0, 1).map((commit) => commit.id);
  });  
  const [isPicking, setIsPicking] = useState(false); // Compare: "Add Commit" was pressed
  const [overlayCommit, setOverlayCommit] = useState(null);

  // Standard shows the latest pick, Compare the latest two (kept in timeline order)
  const shownIds = mode === "standard" ? picks.slice(-1) : picks.slice(-2);
  const shown = commits.filter((c) => shownIds.includes(c.id));

  function handleModeChange(next) {
    setMode(next);
    setIsPicking(false);
    if (next === "standard") setPicks((p) => p.slice(-1));
  }

  function handleSelect(id) {
    setIsPicking(false);
    if (mode === "standard") {
      setPicks([id]);
      return;
    }
    setPicks((prev) => {
      if (prev.includes(id)) return prev.length > 1 ? prev.filter((x) => x !== id) : prev;
      return [...prev, id].slice(-2);
    });
  }

  // Downloads the screenshot(s) currently on screen.
  function handleDownload() {
    shown.filter((commit) => commit.image).forEach((c) => {
      const link = document.createElement("a");
      link.href = c.image;
      link.download = `${project.id}-${c.sha}.png`;
      document.body.appendChild(link);
      link.click();
      link.remove();
    });
  }

  // TODO: call the backend AI endpoint.
  const handleAsk = async () => "The AI Assistant isn’t connected to the backend yet.";

  return (
    <PageLayout width="timeline" watermark="center">
      <div className={styles.page}>
        <p role="status">
          {analysis.status.replaceAll("_", " ")} —{" "}
          {analysis.progress.processed} / {analysis.progress.total} processed
          {" · "}
          {analysis.progress.failed} failed
        </p>

        {analysis.error_message && (
          <p role="alert">{analysis.error_message}</p>
        )}
        <div className={styles.top}>
          <div>
            <BackLink to="/gallery">Back to Gallery</BackLink>

            <div className={styles.titleRow}>
              <h1 className={styles.title}>{project.name}</h1>

              <DownloadButton
                label="Download screenshots"
                onClick={handleDownload}
                disabled={!shown.some((commit) => commit.image)}
              />
            </div>
          </div>
        </div>

        <section className={styles.stage} aria-label="Selected commits" aria-live="polite">
          {mode === "standard" ? (
            <div className={styles.single}>
              {shown[0] && <CommitPreview commit={shown[0]} onOpen={setOverlayCommit} />}
            </div>
          ) : (
            <div className={styles.pair}>
              {shown.map((c) => (
                <CommitPreview key={c.id} commit={c} onOpen={setOverlayCommit} />
              ))}
              {shown.length < 2 && <EmptyCommitSlot isPicking={isPicking} onAdd={() => setIsPicking(true)} />}
            </div>
          )}
        </section>

        <Timeline commits={commits} selectedIds={shownIds} onSelect={handleSelect} />

        <div className={styles.modeRow}>
          <ModeToggle value={mode} onChange={handleModeChange} />
        </div>

        {overlayCommit && <CommitOverlay commit={overlayCommit} onClose={() => setOverlayCommit(null)} />}
        <AIAssistant onAsk={handleAsk} />
      </div>
    </PageLayout>
  );
};

const ProjectTimelineLoader = ({ projectId }) => {
  const { project, error, isLoading } = useProject(projectId);

  if (isLoading) {
    return (
      <PageLayout width="narrow">
        <p role="status">Loading project…</p>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout width="narrow">
        <p role="alert">{error}</p>
        <button onClick={() => window.location.reload()}>
          Retry
        </button>
      </PageLayout>
    );
  }

  if (!project.analysis) {
    return (
      <PageLayout width="narrow">
        <h1>{project.name}</h1>
        <p>This project has no analysis yet.</p>
        <Link to="/new-project">Create a new analysis</Link>
      </PageLayout>
    );
  }

  const commits = project.analysis.commits.map((commit) => ({
    ...commit,
    id: commit.sha,
    image: commit.screenshot_url,
  }));

  return (
    <ProjectTimelineView
      key={project.analysis.job_id}
      project={project}
      commits={commits}
    />
  );
};

const ProjectTimeline = () => {
  const { projectId } = useParams();

  return (
    <ProjectTimelineLoader
      key={projectId}
      projectId={projectId}
    />
  );
};

export default ProjectTimeline;

