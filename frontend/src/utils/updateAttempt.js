// Helpers for the backend's `update_attempt` summary: the newest analysis job of a
// project. The backend decides which job is the "active" one that is displayed.
// An attempt is only a "candidate" while it is not that displayed job.

const MAX_FAILURE_DETAILS = 5;

// True while the worker may still be adding screenshots to the attempt.
export function isUpdateInProgress(attempt) {
  return attempt?.status === "queued" || attempt?.status === "processing";
}

// True when the attempt is a different job from the one currently displayed.
export function isCandidateAttempt(activeJobId, attempt) {
  return Boolean(attempt) && attempt.job_id !== activeJobId;
}

// One line of progress text for an attempt that is queued or processing.
export function describeUpdateProgress(attempt) {
  const label = attempt.status === "queued" ? "Update queued" : "Update in progress";
  const { processed, total, failed } = attempt.progress;
  return `${label} — ${processed} / ${total} processed · ${failed} failed`;
}

// Explains why a finished attempt did not replace the displayed results.
// Returns { summary, details }, where details has one line per failed capture.
export function describeUnfinishedUpdate(attempt) {
  const { succeeded, total } = attempt.progress;
  let summary;

  if (attempt.status === "failed") {
    summary = "The latest update failed, so it did not replace your results.";
  } else if (attempt.status === "partially_complete") {
    summary =
      `The latest update captured ${succeeded} of ${total} selected commits, ` +
      "so it did not replace your results.";
  } else {
    summary =
      "The latest update finished without a complete set of screenshots, " +
      "so it did not replace your results.";
  }

  if (attempt.error_message) summary += " " + attempt.error_message;

  const details = [];
  for (const capture of attempt.captures || []) {
    if (capture.status !== "failed") continue;
    if (details.length === MAX_FAILURE_DETAILS) break;
    details.push(`${capture.commit_sha.slice(0, 7)}: ${capture.error_message || "Capture failed."}`);
  }

  return { summary, details };
}
