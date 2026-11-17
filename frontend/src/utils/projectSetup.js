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

export async function postJSON(path, body, signal) {
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
      throw new Error(getCompatibilityExplanation(data));
    }

    const message = data.error || data.detail || data.reason;
    const fields = Object.entries(data)
      .map(([field, errors]) =>
        field + ": " + (Array.isArray(errors) ? errors.join(" ") : JSON.stringify(errors))
      )
      .join(" ");

    throw new Error(
      (Array.isArray(message) ? message.join(" ") : message) ||
      fields ||
      "The request failed. Please try again."
    );
  }

  return data;
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
  if (!hasValidChoices(review.pages, review.commits, review.selectedIds)) return false;
  if (!review.pages.includes(review.pagePath)) return false;
  for (const commit of review.commits) {
    if (commit.id !== commit.sha) return false;
  }
  return true;
}
