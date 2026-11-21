import assert from "node:assert/strict";
import { test } from "node:test";
import {
  describeUnfinishedUpdate,
  describeUpdateProgress,
  isCandidateAttempt,
  isUpdateInProgress,
} from "../src/utils/updateAttempt.js";

function attempt(overrides = {}) {
  return {
    job_id: "update-job",
    status: "processing",
    error_message: "",
    progress: { total: 4, processed: 2, succeeded: 1, failed: 1 },
    captures: [
      { commit_sha: "a".repeat(40), position: 0, status: "complete", error_message: "" },
      { commit_sha: "b".repeat(40), position: 1, status: "failed", error_message: "Page did not load." },
      { commit_sha: "c".repeat(40), position: 2, status: "pending", error_message: "" },
    ],
    ...overrides,
  };
}

test("only queued and processing attempts are in progress", () => {
  assert.equal(isUpdateInProgress(attempt({ status: "queued" })), true);
  assert.equal(isUpdateInProgress(attempt({ status: "processing" })), true);
  for (const status of ["complete", "partially_complete", "failed"]) {
    assert.equal(isUpdateInProgress(attempt({ status })), false);
  }
  assert.equal(isUpdateInProgress(null), false);
  assert.equal(isUpdateInProgress(undefined), false);
});

test("an attempt is a candidate only when it is not the displayed job", () => {
  assert.equal(isCandidateAttempt("saved-job", attempt()), true);
  assert.equal(isCandidateAttempt("update-job", attempt({ status: "complete" })), false);
  assert.equal(isCandidateAttempt("saved-job", null), false);
});

test("progress text uses the real status and counts", () => {
  assert.equal(
    describeUpdateProgress(attempt()),
    "Update in progress — 2 / 4 processed · 1 failed"
  );
  assert.match(describeUpdateProgress(attempt({ status: "queued" })), /^Update queued/);
});

test("failed and partial updates explain that the old results were kept", () => {
  const failed = describeUnfinishedUpdate(attempt({ status: "failed", error_message: "Worker stopped." }));
  assert.match(failed.summary, /latest update failed/);
  assert.match(failed.summary, /did not replace your results/);
  assert.match(failed.summary, /Worker stopped\./);
  assert.deepEqual(failed.details, ["bbbbbbb: Page did not load."]);

  const partial = describeUnfinishedUpdate(attempt({ status: "partially_complete" }));
  assert.match(partial.summary, /captured 1 of 4 selected commits/);
});

test("a finished update that is not displayed still gets an explanation", () => {
  const unfinished = describeUnfinishedUpdate(attempt({ status: "complete", captures: [] }));
  assert.match(unfinished.summary, /without a complete set of screenshots/);
  assert.deepEqual(unfinished.details, []);
});

test("failure details are capped and always have text", () => {
  const captures = Array.from({ length: 8 }, (_, index) => ({
    commit_sha: String(index).repeat(40), position: index, status: "failed", error_message: "",
  }));
  const { details } = describeUnfinishedUpdate(attempt({ status: "failed", captures }));
  assert.equal(details.length, 5);
  assert.match(details[0], /^0000000: Capture failed\.$/);
});
