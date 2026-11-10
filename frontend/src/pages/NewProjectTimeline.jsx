import { useRef, useState } from "react";
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

const loadScreenshot = (src) => new Promise((resolve, reject) => {
  const image = new Image();
  image.onload = () => resolve(image);
  image.onerror = () => reject(new Error("A screenshot could not be loaded."));
  image.crossOrigin = "anonymous";
  image.src = src;
});

const ProjectTimelineView = ({ project, commits }) => {
  const analysis = project.analysis;
  const [mode, setMode] = useState("standard"); // "standard" | "compare"
  const [picks, setPicks] = useState(() => {
    const latestCaptured = commits.filter((commit) => commit.image).at(-1);

    return latestCaptured
      ? [latestCaptured.id, null]
      : [commits[0]?.id ?? null, null];
  });  
  const [activeSlot, setActiveSlot] = useState(null);
  const [overlayCommit, setOverlayCommit] = useState(null);
  const [downloadError, setDownloadError] = useState("");
  const modeRowRef = useRef(null);

  // Compare slots stay fixed: 1 is left and 2 is right.
  const shownIds = mode === "standard" ? picks.filter(Boolean).slice(-1) : picks.filter(Boolean);
  const shown = shownIds.map((id) => commits.find((commit) => commit.id === id)).filter(Boolean);
  const slotById = mode === "compare"
    ? Object.fromEntries(picks.flatMap((id, index) => id ? [[id, index + 1]] : []))
    : {};

  function handleModeChange(next) {
    const previousTop = modeRowRef.current?.getBoundingClientRect().top;
    setMode(next);
    setActiveSlot(null);
    if (next === "standard") setPicks((p) => [p.filter(Boolean).at(-1) ?? null, null]);
    if (previousTop !== undefined) {
      requestAnimationFrame(() => {
        const nextTop = modeRowRef.current?.getBoundingClientRect().top;
        if (nextTop !== undefined) window.scrollBy(0, nextTop - previousTop);
      });
    }
  }

  function handleSelect(id) {
    if (mode === "standard") {
      setPicks([id, null]);
      return;
    }
    if (!activeSlot) return;

    const targetIndex = activeSlot - 1;
    setPicks((prev) => {
      const next = [...prev];
      const otherIndex = 1 - targetIndex;
      if (next[otherIndex] === id) {
        if (!next[targetIndex]) return prev;
        next[otherIndex] = next[targetIndex];
      }
      next[targetIndex] = id;
      return next;
    });
    setActiveSlot(null);
  }

  async function handleDownload() {
    setDownloadError("");
    const screenshots = shown.filter((commit) => commit.image);

    if (mode === "compare") {
      try {
        const [left, right] = await Promise.all(screenshots.map((commit) => loadScreenshot(commit.image)));
        const gap = 16;
        const canvas = document.createElement("canvas");
        canvas.width = left.naturalWidth + gap + right.naturalWidth;
        canvas.height = Math.max(left.naturalHeight, right.naturalHeight);
        const context = canvas.getContext("2d");
        if (!context) throw new Error("Could not create the comparison image.");
        context.fillStyle = "#fefeff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(left, 0, 0);
        context.drawImage(right, left.naturalWidth + gap, 0);

        const blob = await new Promise((resolve, reject) => {
          canvas.toBlob((result) => {
            if (result) resolve(result);
            else reject(new Error("Could not export the comparison image."));
          }, "image/png");
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${project.id}-comparison.png`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      } catch (error) {
        console.error("Could not download the comparison screenshot.", error);
        setDownloadError("Could not create the comparison download. Please try again.");
      }
      return;
    }

    screenshots.forEach((commit) => {
      const link = document.createElement("a");
      link.href = commit.image;
      link.download = `${project.id}-${commit.sha}.png`;
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
                label={mode === "compare" ? "Download comparison" : "Download screenshots"}
                onClick={handleDownload}
                disabled={mode === "compare"
                  ? shown.length !== 2 || shown.some((commit) => !commit.image)
                  : !shown.some((commit) => commit.image)}
              />
            </div>
            {downloadError && <p role="alert">{downloadError}</p>}
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
              {shown.length < 2 && (
                <EmptyCommitSlot
                  isPicking={activeSlot === 2}
                  onAdd={() => setActiveSlot(2)}
                />
              )}
            </div>
          )}
        </section>

        <Timeline
          commits={commits}
          selectedIds={shownIds}
          slotById={slotById}
          activeSlot={activeSlot}
          comparisonMode={mode === "compare"}
          onSelect={handleSelect}
          onAssignSlot={setActiveSlot}
        />

        <div ref={modeRowRef} className={styles.modeRow}>
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
