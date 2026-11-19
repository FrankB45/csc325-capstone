import { useId, useRef, useState } from "react";
import { useCommitComparison } from "../../hooks/useCommitComparison.js";
import styles from "./Toolbox.module.css";

//Disables the compare functionality and gives a good reason back
function disabledReason(mode, pair) {
  if (mode !== "compare") return "Switch to Compare mode to use this tool.";

  if (pair.length !== 2 || pair[0].position === pair[1].position) {
    return "Select two different commits on the timeline.";
  }

  if (pair.some((commit) => commit.status === "failed")) {
    return "Choose two commits with successful captures.";
  }

  if (pair.some((commit) => commit.status !== "complete" || !commit.image)) {
    return "Both screenshots must finish capturing first.";
  }

  return "";
}
// Really simple way to display the findings... We will need to discuss how we are actually
// going to display these, but for now this works
function Findings({ result }) {
  return (
    <>
      {result.changes.length > 0 ? (
        <ul className={styles.changes}>
          {result.changes.map(({ element, location, description, file_path }, i) => (
            <li key={i}>
              {(element || location) && (
                <strong>{[element, location].filter(Boolean).join(" · ")}</strong>
              )}
              <p>{description}</p>
              {file_path && <code>{file_path}</code>}
            </li>
          ))}
        </ul>
      ) : <p>No visible changes were reported.</p>}

      {result.limitations.length > 0 && (
        <>
          <h3>Limitations</h3>
          <ul>
            {result.limitations.map((text, i) => <li key={i}>{text}</li>)}
          </ul>
        </>
      )}
    </>
  );
}

function PairTools({ jobId, pagePath, pair, reason, open, setOpen }) {
  const { record, busy, compare } = useCommitComparison();
  const panelId = useId();
  const heading = useRef(null);
  const hint = reason || (busy ? "A comparison is in progress." : "");

  function run() {
    if (hint) return;

    compare(jobId, pair[0].position, pair[1].position);
    setOpen(false);
    requestAnimationFrame(() => heading.current?.focus());
  }

  return (
    <>
      <aside className={styles.dock} aria-label="Project tools" data-html2canvas-ignore="true">
        <button
          type="button"
          className={styles.header}
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen(!open)}
        >
          <span className={styles.dot} aria-hidden="true" /> Toolbox
        </button>

        <div id={panelId} className={styles.body} hidden={!open}>
          <button
            type="button"
            className={styles.tool}
            disabled={Boolean(hint)}
            aria-describedby={hint ? `${panelId}-hint` : undefined}
            onClick={run}
          >
            <span aria-hidden="true">✨</span> Compare these two commits
          </button>
          {hint && <p id={`${panelId}-hint`} className={styles.hint}>{hint}</p>}
        </div>
      </aside>

      {record && (
        <section
          className={styles.observations}
          aria-labelledby={`${panelId}-title`}
          data-html2canvas-ignore="true"
        >
          <h2 id={`${panelId}-title`} ref={heading} tabIndex={-1}>
            Observations from compare
          </h2>
          <p className={styles.meta}>
            <code>{pair[0].sha.slice(0, 7)} → {pair[1].sha.slice(0, 7)}</code>
            {pagePath && <> · <code>{pagePath}</code></>}
          </p>

          <div aria-live="polite">
            {busy && (
              <p>{record.status === "queued" ? "Comparison queued…" : "Comparing screenshots…"}</p>
            )}
            {record.status === "complete" && <Findings result={record.result} />}
            {(record.status === "failed" || record.status === "error") && (
              <>
                <p>{record.error_message || "The comparison could not be completed."}</p>
                <button type="button" className={styles.tool} onClick={run}>
                  Retry comparison
                </button>
              </>
            )}
          </div>
        </section>
      )}
    </>
  );
}

export default function Toolbox({ jobId, pagePath, mode, commits }) {
  const [open, setOpen] = useState(false);

  // The backend uses the lower capture position as "before", even if picked second.
  const pair = commits.filter(Boolean).sort((a, b) => a.position - b.position);
  const reason = disabledReason(mode, pair);
  const key = [jobId, mode, ...pair.map((commit) => commit.position), Boolean(reason)].join("/");

  return (
    <PairTools
      key={key}
      jobId={jobId}
      pagePath={pagePath}
      pair={pair}
      reason={reason}
      open={open}
      setOpen={setOpen}
    />
  );
}