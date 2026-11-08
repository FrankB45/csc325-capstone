import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import BackLink from "../components/BackLink/BackLink.jsx";
import DownloadButton from "../components/DownloadButton/DownloadButton.jsx";
import SyncButton from "../components/SyncButton/SyncButton.jsx";
import ModeToggle from "../components/ModeToggle/ModeToggle.jsx";
import CommitPreview from "../components/CommitPreview/CommitPreview.jsx";
import EmptyCommitSlot from "../components/EmptyCommitSlot/EmptyCommitSlot.jsx";
import Timeline from "../components/Timeline/Timeline.jsx";
import CommitOverlay from "../components/CommitOverlay/CommitOverlay.jsx";
import AIAssistant from "../components/AIAssistant/AIAssistant.jsx";
import { MOCK_PROJECTS, getMockCommits } from "../data/mock.js";
import styles from "./ProjectTimeline.module.css";
import watermark from "../assets/octocat-watermark.svg";

const ProjectTimelineView = ({ projectId }) => {
  // TODO: fetch the project and its captured commits from the backend.
  const project = MOCK_PROJECTS.find((p) => p.id === projectId);
  const commits = useMemo(() => getMockCommits(projectId), [projectId]);

  const [mode, setMode] = useState("standard"); // "standard" | "compare"
  const [picks, setPicks] = useState(() => commits.slice(-1).map((c) => c.id)); // selection order; default = newest
  const [isPicking, setIsPicking] = useState(false); // Compare: "Add Commit" was pressed
  const [overlayCommit, setOverlayCommit] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncedAt, setSyncedAt] = useState("1 min ago");

  if (!project) {
    return (
      <PageLayout width="narrow">
        <img className={styles.watermark} src={watermark} alt="" aria-hidden="true" />
        <h1>Project not found</h1>
        <Link to="/gallery">&lt; Back to Gallery</Link>
      </PageLayout>
    );
  }

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

  // TODO: call the backend sync endpoint.
  function handleSync() {
    setIsSyncing(true);
    setTimeout(() => {
      setIsSyncing(false);
      setSyncedAt("just now");
    }, 1500);
  }

  // Downloads the screenshot(s) currently on screen.
  // TODO: switch to a backend export once it exists (browsers ignore `download` on cross-origin URLs).
  function handleDownload() {
    shown.forEach((c) => {
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
        <div className={styles.top}>
          <div>
            <BackLink to="/gallery">Back to Gallery</BackLink>
            <div className={styles.titleRow}>
              <h1 className={styles.title}>{project.name}</h1>
              <DownloadButton label="Download screenshots" onClick={handleDownload} disabled={shown.length === 0} />
            </div>
          </div>

          <div className={styles.sync}>
            <SyncButton syncing={isSyncing} onClick={handleSync} />
            <p className={styles.syncText}>Last sync: {syncedAt}</p>
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

// key= resets mode/selection when navigating between projects
const ProjectTimeline = () => {
  const { projectId } = useParams();
  return <ProjectTimelineView key={projectId} projectId={projectId} />;
};

export default ProjectTimeline;
