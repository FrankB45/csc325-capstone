import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import Button from "../components/Button/Button.jsx";
import ModeToggle from "../components/ModeToggle/ModeToggle.jsx";
import Timeline from "../components/Timeline/Timeline.jsx";
import Modal from "../components/Modal/Modal.jsx";
import AIAssistant from "../components/AIAssistant/AIAssistant.jsx";
import { MOCK_COMMITS, MOCK_PROJECTS } from "../data/mock.js";
import { formatDate } from "../utils/format.js";
import styles from "./ProjectTimeline.module.css";

const ProjectTimelineView = ({ projectId }) => {
  // TODO: fetch the project + its captured commits from the backend.
  const project = MOCK_PROJECTS.find((p) => p.id === projectId);
  const commits = MOCK_COMMITS.slice(0, project?.commitCount ?? 0);

  const [mode, setMode] = useState("standard");
  // null = "use the default for this mode" (latest commit, or latest two in Compare)
  const [picks, setPicks] = useState({ standard: null, compare: null });
  const [expanded, setExpanded] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncedAt, setSyncedAt] = useState("1 min ago");

  const closeOverlay = useCallback(() => setExpanded(null), []);

  const defaultIds = commits.map((c) => c.id).slice(mode === "standard" ? -1 : -2);
  const selectedIds = picks[mode] ?? defaultIds;

  if (!project) {
    return (
      <PageLayout width="narrow">
        <h1>Project not found</h1>
        <Link to="/gallery">&lt; Back to Gallery</Link>
      </PageLayout>
    );
  }

  const select = (id) => {
    let next;
    if (mode === "standard") next = [id];
    else if (selectedIds.includes(id)) next = selectedIds.filter((x) => x !== id);
    else next = [...selectedIds, id].slice(-2); // compare: keep the two most recent picks
    setPicks((p) => ({ ...p, [mode]: next }));
  };

  // TODO: call the backend sync endpoint.
  const handleSync = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setIsSyncing(false);
      setSyncedAt("just now");
    }, 1500);
  };

  // TODO: call the backend AI endpoint.
  const handleAsk = async () => "The AI Assistant isn’t connected to the backend yet.";

  const selected = commits
    .filter((c) => selectedIds.includes(c.id))
    .sort((a, b) => a.date.localeCompare(b.date));

  return (
    <PageLayout width="wide">
      <Link to="/gallery" className={styles.back}>&lt; Back to Gallery</Link>

      <div className={styles.top}>
        <div>
          <h1 className={styles.title}>{project.name}</h1>
          <p className={styles.sync}>Last sync: {syncedAt}</p>
        </div>
        <div className={styles.controls}>
          <Button size="sm" variant="secondary" loading={isSyncing} onClick={handleSync}>Sync Updates</Button>
          <Button size="sm" disabled title="Coming soon">Add Commit</Button>
          <ModeToggle value={mode} onChange={setMode} />
        </div>
      </div>

      <section className={`${styles.preview} ${mode === "compare" ? styles.previewCompare : ""}`} aria-live="polite">
        {selected.length === 0 && <p className={styles.hint}>Select a commit below to preview it.</p>}
        {selected.map((c) => (
          <figure key={c.id} className={styles.figure}>
            <img src={c.image} alt={`Screenshot at commit: ${c.message}`} />
            <figcaption>{c.message} · {formatDate(c.date)}</figcaption>
          </figure>
        ))}
        {mode === "compare" && selected.length === 1 && (
          <p className={styles.hint}>Select a second commit to compare.</p>
        )}
      </section>

      <Timeline commits={commits} selectedIds={selectedIds} onSelect={select} onExpand={setExpanded} />

      {expanded && (
        <Modal title={`Screenshot: ${expanded.message}`} onClose={closeOverlay}>
          <img src={expanded.image} alt={`Full screenshot at commit: ${expanded.message}`} />
        </Modal>
      )}

      <AIAssistant onAsk={handleAsk} />
    </PageLayout>
  );
};

// key= resets selection/mode state when navigating between projects
const ProjectTimeline = () => {
  const { projectId } = useParams();
  return <ProjectTimelineView key={projectId} projectId={projectId} />;
};

export default ProjectTimeline;
