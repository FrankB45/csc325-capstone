// Mirrors backend/commit_selection.py. `commits` is ordered oldest -> newest.
export const MIN_SELECTED = 1;
export const MAX_SELECTED = 10;
export const RULE_MESSAGE = "Select between 1 and 10 commits to start capture.";

export function defaultSelection(commits) {
  const n = commits.length;
  if (n <= MAX_SELECTED) return commits.map((c) => c.sha);
  const steps = MAX_SELECTED - 1;
  return Array.from({ length: MAX_SELECTED }, (_, i) =>
    commits[Math.floor((2 * i * (n - 1) + steps) / (2 * steps))].sha
  );
}