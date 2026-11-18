import { MAX_COMMITS, MIN_COMMITS } from "./commits.js";

const INVALID_SETUP =
  "The server returned incomplete or invalid setup information. Please try again.";

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function getCompatibilityExplanation(report) {
  const checks = [
    [report.history?.history_status, report.history?.reason],
    [report.html?.html_status, report.html?.reason],
    [report.dependencies?.status, report.dependencies?.reason],
  ];

  for (const [status, reason] of checks) {
    if (status === report.overall_status && typeof reason === "string" && reason.trim()) {
      return reason;
    }
  }

  if (typeof report.reason === "string" && report.reason.trim()) return report.reason;
  return "Compatibility could not be confirmed. Please try again.";
}

// Sends a JSON POST and returns { status, data }. Use postJSON when only the data matters.
export async function postJSONWithStatus(path, body, signal) {
  if (signal?.aborted) throw new DOMException("Request canceled.", "AbortError");

  let response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (signal?.aborted || error.name === "AbortError") {
      throw new DOMException("Request canceled.", "AbortError");
    }
    throw new Error("Could not reach the server. Please try again.", { cause: error });
  }

  let data;
  try {
    data = await response.json();
  } catch (error) {
    if (signal?.aborted || error.name === "AbortError") {
      throw new DOMException("Request canceled.", "AbortError");
    }
    throw new Error("The server returned an unreadable response. Please try again.", { cause: error });
  }

  if (signal?.aborted) throw new DOMException("Request canceled.", "AbortError");
  if (!isObject(data)) throw new Error(INVALID_SETUP);

  if (!response.ok) {
    // HTTP 502 can contain a useful compatibility report, not just a generic error.
    if (data.overall_status === "unavailable") {
      throw requestError(getCompatibilityExplanation(data), response.status);
    }

    const message = data.error || data.detail || data.reason;
    const fields = Object.entries(data)
      .map(([field, errors]) =>
        field + ": " + (Array.isArray(errors) ? errors.join(" ") : JSON.stringify(errors))
      )
      .join(" ");

    throw requestError(
      (Array.isArray(message) ? message.join(" ") : message) ||
      fields ||
      "The request failed. Please try again.",
      response.status
    );
  }

  return { status: response.status, data };
}

export async function postJSON(path, body, signal) {
  const { data } = await postJSONWithStatus(path, body, signal);
  return data;
}

// An error for a readable HTTP error response. Network failures and unreadable
// responses have no httpStatus, which is how callers know the server's answer is unknown.
function requestError(message, httpStatus) {
  const error = new Error(message);
  error.httpStatus = httpStatus;
  return error;
}

function hasValidChoices(pages, commits, selectedIds) {
  if (!Array.isArray(pages) || pages.length === 0) return false;
  const knownPages = [];
  for (const page of pages) {
    if (typeof page !== "string" || !page.trim() || knownPages.includes(page)) return false;
    knownPages.push(page);
  }

  if (!Array.isArray(commits) || commits.length === 0) return false;
  const knownShas = [];
  for (const commit of commits) {
    if (
      !isObject(commit) ||
      typeof commit.sha !== "string" ||
      !/^[0-9a-f]{40}$/.test(commit.sha) ||
      knownShas.includes(commit.sha) ||
      typeof commit.message !== "string" ||
      typeof commit.date !== "string" ||
      Number.isNaN(Date.parse(commit.date))
    ) return false;
    knownShas.push(commit.sha);
  }

  if (
    !Array.isArray(selectedIds) ||
    selectedIds.length < MIN_COMMITS ||
    selectedIds.length > MAX_COMMITS
  ) return false;

  const selectedShas = [];
  for (const sha of selectedIds) {
    if (!knownShas.includes(sha) || selectedShas.includes(sha)) return false;
    selectedShas.push(sha);
  }
  return true;
}

export async function prepareProjectSetup(url, signal) {
  if (typeof url !== "string" || !url.trim()) {
    throw new Error("This project has no saved repository URL to check.");
  }

  const report = await postJSON("/api/repo/compatibility/", { url }, signal);
  const statuses = ["accepted", "rejected", "pending", "unavailable"];
  if (!statuses.includes(report.overall_status) || typeof report.setup_available !== "boolean") {
    throw new Error(INVALID_SETUP);
  }

  if (report.overall_status !== "accepted") {
    if (report.setup_available) throw new Error(INVALID_SETUP);
    throw new Error(getCompatibilityExplanation(report));
  }

  if (
    !report.setup_available ||
    report.history?.history_status !== "passed" ||
    report.html?.html_status !== "passed" ||
    report.dependencies?.status !== "passed"
  ) throw new Error(INVALID_SETUP);

  const pages = report.html.html_pages;
  if (!Array.isArray(pages) || pages.length === 0) throw new Error(INVALID_SETUP);

  const history = await postJSON("/api/repo/commits/", { url }, signal);
  if (!hasValidChoices(pages, history.commits, history.preselected)) {
    throw new Error(INVALID_SETUP);
  }

  return {
    pages: [...pages],
    pagePath: pages.find((page) => page.toLowerCase() === "index.html") || pages[0],
    commits: history.commits.map((commit) => ({ ...commit, id: commit.sha })),
    selectedIds: [...history.preselected],
  };
}

export function isValidUpdateReview(review) {
  if (!isObject(review)) return false;
  for (const field of ["sourceProjectId", "sourceJobId", "repositoryUrl", "projectTitle"]) {
    if (typeof review[field] !== "string" || !review[field].trim()) return false;
  }
  // The newest update attempt known when review opened: null means there was none yet.
  const attemptId = review.sourceAttemptJobId;
  if (attemptId !== null && (typeof attemptId !== "string" || !attemptId.trim())) return false;
  if (!hasValidChoices(review.pages, review.commits, review.selectedIds)) return false;
  if (!review.pages.includes(review.pagePath)) return false;
  for (const commit of review.commits) {
    if (commit.id !== commit.sha) return false;
  }
  return true;
}

// Only these statuses come from checks that run before any job is saved, so a
// readable JSON reply with one of them means no update was started.
const NOT_STARTED_STATUSES = [400, 404, 409];

function notStartedError(message) {
  const error = new Error(message);
  error.outcomeUnknown = false;
  return error;
}

function unknownOutcomeError(message) {
  const error = new Error(message);
  error.outcomeUnknown = true;
  return error;
}

// Sends one update request. Never retries. Returns { jobId } for an accepted update.
// A thrown error has outcomeUnknown = false only when the server clearly refused the
// update. Anything else (lost reply, timeout, unreadable or unexpected reply) is unknown.
export async function submitProjectUpdate(review, signal) {
  if (!isValidUpdateReview(review)) {
    throw notStartedError("Update review could not be opened. Return to the project and check again.");
  }

  let reply;
  try {
    reply = await postJSONWithStatus(
      "/api/analyses/",
      {
        url: review.repositoryUrl,
        name: review.projectTitle,
        page_path: review.pagePath,
        commit_shas: review.selectedIds,
        project_id: review.sourceProjectId,
        source_job_id: review.sourceJobId,
      },
      signal
    );
  } catch (error) {
    if (error.name === "AbortError") throw error;
    error.outcomeUnknown = !NOT_STARTED_STATUSES.includes(error.httpStatus);
    throw error;
  }

  // The server accepts an update with HTTP 202 only. Any other success status, or a 202
  // for a different project or without a job ID, cannot be trusted.
  const result = reply.data;
  if (
    reply.status !== 202 ||
    typeof result.job_id !== "string" ||
    !result.job_id.trim() ||
    result.project_id !== review.sourceProjectId
  ) {
    throw unknownOutcomeError("The server's reply could not be confirmed.");
  }

  return { jobId: result.job_id };
}

export const NO_NEW_UPDATE_MESSAGE =
  "No new update is visible yet. The earlier request may still be reaching the server, " +
  "so this does not mean it failed. Check again shortly or go back to the project.";

// Reads the project once and returns its newest update attempt if it is different
// from the one known before submitting. Returns null when no new attempt is visible.
// "Not visible" never proves that the earlier request failed.
export async function findNewUpdateAttempt(projectId, knownAttemptJobId, signal) {
  const failureMessage = "Could not check the project. Please try again.";
  let data;

  try {
    const response = await fetch("/api/projects/" + encodeURIComponent(projectId) + "/", { signal });
    data = await response.json();
    if (!response.ok) throw new Error(failureMessage);
  } catch (error) {
    if (signal?.aborted || error.name === "AbortError") {
      throw new DOMException("Request canceled.", "AbortError");
    }
    throw new Error(failureMessage, { cause: error });
  }

  if (signal?.aborted) throw new DOMException("Request canceled.", "AbortError");
  if (!isObject(data) || !("update_attempt" in data)) throw new Error(failureMessage);

  const attempt = data.update_attempt;
  if (attempt === null) return null;
  if (!isObject(attempt) || typeof attempt.job_id !== "string" || !attempt.job_id) {
    throw new Error(failureMessage);
  }

  return attempt.job_id === knownAttemptJobId ? null : attempt;
}
