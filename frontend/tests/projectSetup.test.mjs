import assert from "node:assert/strict";
import { test } from "node:test";
import {
  findNewUpdateAttempt,
  isValidUpdateReview,
  postJSON,
  postJSONWithStatus,
  prepareProjectSetup,
  submitProjectUpdate,
} from "../src/utils/projectSetup.js";

const repositoryUrl = "https://github.com/example/saved-project";
const firstSha = "a".repeat(40);
const secondSha = "b".repeat(40);

function acceptedReport() {
  return {
    overall_status: "accepted",
    setup_available: true,
    history: { history_status: "passed", reason: "History passed." },
    html: { html_status: "passed", html_pages: ["pages/about.html", "INDEX.HTML"] },
    dependencies: { status: "passed", reason: "Dependencies passed." },
  };
}

function commitChoices() {
  return {
    commits: [
      { sha: firstSha, message: "Fresh first commit", date: "2026-11-17T10:00:00Z" },
      { sha: secondSha, message: "Fresh second commit", date: "2026-11-17T11:00:00Z" },
    ],
    preselected: [firstSha, secondSha],
  };
}

function mockRequests(t, responses) {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (path, options) => {
    calls.push({ path, ...options, body: JSON.parse(options.body) });
    assert.notEqual(path, "/api/analyses/", "Setup preparation must never submit an analysis.");
    const response = responses[calls.length - 1];
    assert.ok(response, "Unexpected request: " + path);
    if (typeof response === "function") return response();
    return new Response(JSON.stringify(response.body), { status: response.status || 200 });
  });
  return calls;
}

test("uses the saved URL for both requests and returns fresh independent choices", async (t) => {
  const report = acceptedReport();
  const history = commitChoices();
  const calls = mockRequests(t, [{ body: report }, { body: history }]);
  const setup = await prepareProjectSetup(repositoryUrl);

  assert.deepEqual(calls.map((call) => call.path), [
    "/api/repo/compatibility/", "/api/repo/commits/",
  ]);
  for (const call of calls) {
    assert.equal(call.method, "POST");
    assert.deepEqual(call.body, { url: repositoryUrl });
  }
  assert.deepEqual(setup.pages, report.html.html_pages);
  assert.equal(setup.pagePath, "INDEX.HTML");
  assert.deepEqual(setup.commits.map((commit) => commit.id), [firstSha, secondSha]);
  assert.deepEqual(setup.selectedIds, history.preselected);
  setup.pages.push("draft.html");
  setup.selectedIds.pop();
  assert.equal(report.html.html_pages.length, 2);
  assert.equal(history.preselected.length, 2);
});

test("uses the first page when a root homepage is absent from the returned choices", async (t) => {
  const report = acceptedReport();
  report.html.html_pages = ["pages/about.html"];
  mockRequests(t, [{ body: report }, { body: commitChoices() }]);
  assert.equal((await prepareProjectSetup(repositoryUrl)).pagePath, "pages/about.html");
});

test("reports the matching rejection instead of another check's temporary failure", async (t) => {
  const report = acceptedReport();
  report.overall_status = "rejected";
  report.setup_available = false;
  report.history = { history_status: "unavailable", reason: "History temporarily unavailable." };
  report.dependencies = { status: "rejected", reason: "A required backend is unsupported." };
  const calls = mockRequests(t, [{ body: report }]);
  await assert.rejects(prepareProjectSetup(repositoryUrl), /required backend is unsupported/);
  assert.equal(calls.length, 1);
});

test("pending and unavailable reports retain their specific explanations", async (t) => {
  for (const status of ["pending", "unavailable"]) {
    await t.test(status, async (t) => {
      const report = acceptedReport();
      report.overall_status = status;
      report.setup_available = false;
      report.dependencies = { status, reason: "Dependency inspection needs another attempt." };
      const calls = mockRequests(t, [{ body: report, status: status === "unavailable" ? 502 : 200 }]);
      await assert.rejects(prepareProjectSetup(repositoryUrl), /Dependency inspection needs another attempt/);
      assert.equal(calls.length, 1);
    });
  }
});

test("falls back to the report explanation when no individual reason is present", async (t) => {
  mockRequests(t, [{ body: {
    overall_status: "pending", setup_available: false, reason: "Please check again later.",
  } }]);
  await assert.rejects(prepareProjectSetup(repositoryUrl), /Please check again later/);
});

test("rejects missing URLs before making any request", async (t) => {
  const calls = mockRequests(t, []);
  for (const url of [undefined, null, "", " "]) {
    await assert.rejects(prepareProjectSetup(url), /no saved repository URL/);
  }
  assert.equal(calls.length, 0);
});

test("accepted requires both decision fields and passed check results", async (t) => {
  const cases = [
    { ...acceptedReport(), setup_available: false },
    { ...acceptedReport(), setup_available: "true" },
    { ...acceptedReport(), overall_status: "unknown" },
    { ...acceptedReport(), history: undefined },
    { ...acceptedReport(), dependencies: { status: "pending" } },
    { ...acceptedReport(), overall_status: "rejected" },
  ];
  for (const [index, report] of cases.entries()) {
    await t.test(String(index), async (t) => {
      const calls = mockRequests(t, [{ body: report }]);
      await assert.rejects(prepareProjectSetup(repositoryUrl), /incomplete or invalid/);
      assert.equal(calls.length, 1);
    });
  }
});

test("empty or missing pages do not open setup or request commits", async (t) => {
  for (const pages of [undefined, null, []]) {
    await t.test(JSON.stringify(pages), async (t) => {
      const report = acceptedReport();
      report.html.html_pages = pages;
      const calls = mockRequests(t, [{ body: report }]);
      await assert.rejects(prepareProjectSetup(repositoryUrl), /incomplete or invalid/);
      assert.equal(calls.length, 1);
    });
  }
});

test("malformed page and commit choices fail closed", async (t) => {
  const cases = [
    { pages: ["INDEX.HTML", "INDEX.HTML"] },
    { pages: [null] },
    { commits: [] },
    { commits: [null] },
    { commits: [{ sha: "short", message: "Bad SHA", date: "2026-11-17" }] },
    { commits: [commitChoices().commits[0], commitChoices().commits[0]] },
    { commits: [{ ...commitChoices().commits[0], date: "invalid" }] },
    { commits: [{ ...commitChoices().commits[0], message: null }] },
    { selectedIds: [] },
    { selectedIds: [firstSha, firstSha] },
    { selectedIds: ["c".repeat(40)] },
    { selectedIds: Array(11).fill(firstSha) },
  ];
  for (const [index, changes] of cases.entries()) {
    await t.test(String(index), async (t) => {
      const report = acceptedReport();
      const history = commitChoices();
      if ("pages" in changes) report.html.html_pages = changes.pages;
      if ("commits" in changes) history.commits = changes.commits;
      if ("selectedIds" in changes) history.preselected = changes.selectedIds;
      mockRequests(t, [{ body: report }, { body: history }]);
      await assert.rejects(prepareProjectSetup(repositoryUrl), /incomplete or invalid/);
    });
  }
});

test("network and unreadable responses have retryable messages", async (t) => {
  const cases = [
    [() => { throw new TypeError("Failed to fetch"); }, /Could not reach the server/],
    [() => new Response("not JSON"), /unreadable response/],
    [{ body: null }, /incomplete or invalid/],
    [{ body: [] }, /incomplete or invalid/],
  ];
  for (const [index, [response, message]] of cases.entries()) {
    await t.test(String(index), async (t) => {
      mockRequests(t, [response]);
      await assert.rejects(prepareProjectSetup(repositoryUrl), message);
    });
  }
});

test("a failed request can be retried with fresh responses", async (t) => {
  const report = { ...acceptedReport(), overall_status: "pending", setup_available: false, reason: "Not ready." };
  const calls = mockRequests(t, [{ body: report }, { body: acceptedReport() }, { body: commitChoices() }]);
  await assert.rejects(prepareProjectSetup(repositoryUrl), /Not ready/);
  assert.equal((await prepareProjectSetup(repositoryUrl)).commits.length, 2);
  assert.equal(calls.length, 3);
});

test("an already aborted request sends nothing", async (t) => {
  const controller = new AbortController();
  controller.abort();
  const calls = mockRequests(t, []);
  await assert.rejects(prepareProjectSetup(repositoryUrl, controller.signal), { name: "AbortError" });
  assert.equal(calls.length, 0);
});

test("late compatibility and commit responses are ignored after abort", async (t) => {
  for (const stage of ["compatibility", "commits"]) {
    await t.test(stage, async (t) => {
      const controller = new AbortController();
      const lateResponse = () => {
        controller.abort();
        return new Response(JSON.stringify(stage === "compatibility" ? acceptedReport() : commitChoices()));
      };
      const responses = stage === "compatibility"
        ? [lateResponse]
        : [{ body: acceptedReport() }, lateResponse];
      const calls = mockRequests(t, responses);
      await assert.rejects(prepareProjectSetup(repositoryUrl, controller.signal), { name: "AbortError" });
      assert.equal(calls.length, responses.length);
    });
  }
});

test("explicit update-review context must have valid source identities and choices", async (t) => {
  mockRequests(t, [{ body: acceptedReport() }, { body: commitChoices() }]);
  const review = {
    sourceProjectId: "saved-project-id",
    sourceJobId: "saved-job-id",
    sourceAttemptJobId: null,
    repositoryUrl,
    projectTitle: "Saved project",
    ...await prepareProjectSetup(repositoryUrl),
  };
  assert.equal(isValidUpdateReview(review), true);
  assert.equal(isValidUpdateReview({ ...review, sourceAttemptJobId: "earlier-attempt-id" }), true);
  for (const invalid of [
    undefined, null, [], {},
    { ...review, sourceProjectId: "" },
    { ...review, sourceJobId: null },
    { ...review, sourceAttemptJobId: undefined },
    { ...review, sourceAttemptJobId: " " },
    { ...review, repositoryUrl: " " },
    { ...review, projectTitle: null },
    { ...review, pagePath: "missing.html" },
    { ...review, selectedIds: ["unknown"] },
    { ...review, commits: review.commits.map((commit) => ({ ...commit, id: "wrong" })) },
  ]) assert.equal(isValidUpdateReview(invalid), false);
});

test("ordinary request errors retain field-validation details", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response(
    JSON.stringify({ commit_shas: ["Select between 1 and 10 commits."] }), { status: 400 }
  ));
  await assert.rejects(postJSON("/api/analyses/", {}), /commit_shas: Select between 1 and 10 commits/);
});

// ---- Submitting an update ----

function updateReview(overrides = {}) {
  return {
    sourceProjectId: "saved-project-id",
    sourceJobId: "saved-job-id",
    sourceAttemptJobId: null,
    repositoryUrl,
    projectTitle: "Saved project",
    pages: ["index.html", "about.html"],
    pagePath: "about.html",
    commits: [
      { sha: firstSha, id: firstSha, message: "First", date: "2026-11-17T10:00:00Z" },
      { sha: secondSha, id: secondSha, message: "Second", date: "2026-11-17T11:00:00Z" },
    ],
    selectedIds: [secondSha],
    ...overrides,
  };
}

// Answers each request with the next response and records every call.
function mockUpdateRequests(t, responses) {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (path, options) => {
    calls.push({ path, method: options?.method || "GET", body: options?.body ? JSON.parse(options.body) : null });
    const response = responses[calls.length - 1];
    assert.ok(response, "Unexpected request: " + path);
    if (response === "network") throw new TypeError("Failed to fetch");
    if (response === "unreadable") return new Response("<html>Bad gateway</html>", { status: 502 });
    return new Response(JSON.stringify(response.body), { status: response.status });
  });
  return calls;
}

const acceptedReply = {
  status: 202,
  body: { job_id: "new-job-id", project_id: "saved-project-id", snapshot_id: "s", status: "queued", total_captures: 1 },
};

test("update submission sends the exact payload with paired source identities", async (t) => {
  const calls = mockUpdateRequests(t, [acceptedReply]);
  const result = await submitProjectUpdate(updateReview());

  assert.deepEqual(result, { jobId: "new-job-id" });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, "/api/analyses/");
  assert.equal(calls[0].method, "POST");
  assert.deepEqual(calls[0].body, {
    url: repositoryUrl,
    name: "Saved project",
    page_path: "about.html",
    commit_shas: [secondSha],
    project_id: "saved-project-id",
    source_job_id: "saved-job-id",
  });
});

test("an invalid review sends nothing and never falls back to ordinary creation", async (t) => {
  const calls = mockUpdateRequests(t, []);
  for (const review of [
    updateReview({ sourceJobId: "" }),
    updateReview({ sourceProjectId: null }),
    updateReview({ pagePath: "missing.html" }),
    updateReview({ selectedIds: [] }),
    null,
  ]) {
    await assert.rejects(submitProjectUpdate(review), (error) => error.outcomeUnknown === false);
  }
  assert.equal(calls.length, 0);
});

test("clear refusals (400, 404, 409) are known not to have started an update", async (t) => {
  for (const [status, body, message] of [
    [400, { error: "Select between 1 and 10 commits." }, /Select between 1 and 10 commits/],
    [400, { commit_shas: ["Not a valid commit."] }, /commit_shas: Not a valid commit/],
    [404, { error: "Project not found." }, /Project not found/],
    [409, { error: "The saved analysis has changed." }, /saved analysis has changed/],
  ]) {
    await t.test(String(status), async (t) => {
      const calls = mockUpdateRequests(t, [{ status, body }]);
      await assert.rejects(submitProjectUpdate(updateReview()), (error) => {
        assert.equal(error.outcomeUnknown, false);
        assert.match(error.message, message);
        return true;
      });
      assert.equal(calls.length, 1, "A refused update must never be retried automatically.");
    });
  }
});

test("server errors, lost replies and unreadable replies leave the outcome unknown", async (t) => {
  for (const [name, response] of [
    ["500 with JSON", { status: 500, body: { error: "Server error." } }],
    ["502 with JSON", { status: 502, body: { error: "GitHub could not complete the request." } }],
    ["504 with JSON", { status: 504, body: { error: "Timed out." } }],
    ["network failure", "network"],
    ["unreadable body", "unreadable"],
    ["non-object JSON", { status: 202, body: ["not", "an", "object"] }],
  ]) {
    await t.test(name, async (t) => {
      const calls = mockUpdateRequests(t, [response]);
      await assert.rejects(submitProjectUpdate(updateReview()), (error) => error.outcomeUnknown === true);
      assert.equal(calls.length, 1, "An unknown outcome must never be retried automatically.");
    });
  }
});

test("an accepted reply for another project or without a job ID is not trusted", async (t) => {
  for (const body of [
    { job_id: "new-job-id", project_id: "another-project-id" },
    { project_id: "saved-project-id" },
    { job_id: "", project_id: "saved-project-id" },
    { job_id: 7, project_id: "saved-project-id" },
  ]) {
    mockUpdateRequests(t, [{ status: 202, body }]);
    await assert.rejects(submitProjectUpdate(updateReview()), (error) => error.outcomeUnknown === true);
    t.mock.restoreAll();
  }
});

test("only HTTP 202 confirms acceptance; other success statuses stay unknown", async (t) => {
  // The same valid body is accepted with 202 but not with any other success status.
  for (const status of [200, 201, 203, 207, 299]) {
    await t.test("status " + status, async (t) => {
      const calls = mockUpdateRequests(t, [{ status, body: acceptedReply.body }]);
      await assert.rejects(
        submitProjectUpdate(updateReview()),
        (error) => error.outcomeUnknown === true && /could not be confirmed/.test(error.message)
      );
      assert.equal(calls.length, 1, "An unexpected success status must never be retried automatically.");
    });
  }

  mockUpdateRequests(t, [acceptedReply]);
  assert.deepEqual(await submitProjectUpdate(updateReview()), { jobId: "new-job-id" });
});

test("a 202 with a malformed body stays unknown", async (t) => {
  for (const body of [
    {},
    { job_id: "new-job-id" },
    { project_id: "saved-project-id" },
    { job_id: "   ", project_id: "saved-project-id" },
    { job_id: "new-job-id", project_id: "another-project-id" },
  ]) {
    mockUpdateRequests(t, [{ status: 202, body }]);
    await assert.rejects(submitProjectUpdate(updateReview()), (error) => error.outcomeUnknown === true);
    t.mock.restoreAll();
  }
});

test("postJSON still returns only the parsed body, and postJSONWithStatus adds the status", async (t) => {
  mockUpdateRequests(t, [{ status: 200, body: { value: 1 } }, { status: 202, body: { value: 2 } }]);
  assert.deepEqual(await postJSON("/api/example/", {}), { value: 1 });
  assert.deepEqual(await postJSONWithStatus("/api/example/", {}), { status: 202, data: { value: 2 } });
});

test("an aborted update request reports an abort, not a failure or success", async (t) => {
  const calls = mockUpdateRequests(t, [acceptedReply]);
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(submitProjectUpdate(updateReview(), controller.signal), { name: "AbortError" });
  assert.equal(calls.length, 0);
});

// ---- Checking for an update after an unclear reply ----

test("checking finds a different attempt and reports its real status", async (t) => {
  for (const status of ["queued", "processing", "complete", "partially_complete", "failed"]) {
    await t.test(status, async (t) => {
      const calls = mockUpdateRequests(t, [{ status: 200, body: { update_attempt: { job_id: "new-job-id", status } } }]);
      const attempt = await findNewUpdateAttempt("saved-project-id", "earlier-attempt", undefined);
      assert.equal(attempt.job_id, "new-job-id");
      assert.equal(attempt.status, status);
      assert.deepEqual(calls.map((call) => [call.method, call.path]), [["GET", "/api/projects/saved-project-id/"]]);
    });
  }
});

test("checking finds nothing when the attempt is missing or unchanged, which proves nothing", async (t) => {
  mockUpdateRequests(t, [{ status: 200, body: { update_attempt: null } }]);
  assert.equal(await findNewUpdateAttempt("p", null), null);
  t.mock.restoreAll();
  mockUpdateRequests(t, [{ status: 200, body: { update_attempt: { job_id: "same", status: "failed" } } }]);
  assert.equal(await findNewUpdateAttempt("p", "same"), null);
});

test("a failed or malformed check is an error, not 'nothing started'", async (t) => {
  for (const response of [
    "network",
    "unreadable",
    { status: 500, body: { error: "oops" } },
    { status: 200, body: {} },
    { status: 200, body: { update_attempt: { status: "queued" } } },
    { status: 200, body: [] },
  ]) {
    mockUpdateRequests(t, [response]);
    await assert.rejects(findNewUpdateAttempt("p", null), /Could not check the project/);
    t.mock.restoreAll();
  }
});

test("an aborted check reports an abort", async (t) => {
  mockUpdateRequests(t, [{ status: 200, body: { update_attempt: null } }]);
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(findNewUpdateAttempt("p", null, controller.signal), { name: "AbortError" });
});
