export const MAX_COMMITS = 10;
export const MIN_COMMITS = 1;

/**
 * Default selection: all commits if there are <= max, otherwise `max` evenly
 * spaced commits that always include the first and the last.
 * `commits` must be ordered oldest -> newest. Returns an array of ids.
 */
export function preselectCommits(commits, max = MAX_COMMITS) {
  if (commits.length <= max) return commits.map((c) => c.id);
  if (max === 1) return [commits[commits.length - 1].id];

  const picked = new Set();
  for (let i = 0; i < max; i++) {
    picked.add(Math.round((i * (commits.length - 1)) / (max - 1)));
  }
  return [...picked].sort((a, b) => a - b).map((i) => commits[i].id);
}
