"""Run with backend/.venv/bin/python frontend/tests/test_update_review_browser.py.

Uses fresh Vite output and an offline browser. All assets and APIs are fulfilled
locally; no server, database, worker, or real analysis is involved. A failed build
may emit usable assets: these checks do not certify a successful production build
or exercise timeline PNG exports that require html2canvas. Every response below is
synthetic, so none of this is live end-to-end verification.
"""

import base64
import json
import mimetypes
import re
import time
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright


FRONTEND = Path(__file__).resolve().parents[1]
DIST = FRONTEND / "dist"
ORIGIN = "http://us12.test"
TIMELINE = ORIGIN + "/projects/saved-project/timeline"
SAVED_URL = "https://github.com/example/saved-project"
OTHER_URL = "https://github.com/example/other-project"
FIRST_SHA = "1" * 40
SECOND_SHA = "2" * 40
FRESH_SHAS = ["a" * 40, "b" * 40]
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aK1sAAAAASUVORK5CYII="
)


ACCEPTED = {
    "job_id": "update-job", "project_id": "saved-project", "snapshot_id": "update-snapshot",
    "status": "queued", "total_captures": 1,
}


def reply(status, body):
    return {"kind": "reply", "status": status, "body": body}


def hold(status, body):
    return {"kind": "hold", "status": status, "body": body}


def saved_project(project_id="saved-project", url=SAVED_URL, name="Saved project", job_id=None, shas=None):
    job_id = job_id or project_id + "-job"
    return {
        "id": project_id, "name": name, "repository_url": url,
        "update_attempt": None,
        "analysis": {
            "job_id": job_id, "snapshot_id": project_id + "-snapshot",
            "page_path": "index.html", "default_page": "index.html",
            "available_pages": ["index.html", "saved/about.html"],
            "status": "complete", "error_message": "",
            "created_at": "2026-11-16T10:00:00Z", "completed_at": "2026-11-16T10:01:00Z",
            "progress": {"total": 2, "processed": 2, "succeeded": 2, "failed": 0},
            "commits": [
                {
                    "sha": sha, "message": "Saved commit " + str(index + 1),
                    "author_name": "Saved author " + str(index + 1),
                    "date": "2026-11-16T10:00:00Z", "status": "complete",
                    "error_message": "", "position": index,
                    "screenshot_url": f"/api/jobs/{job_id}/captures/{index}/image/",
                }
                for index, sha in enumerate(shas or [FIRST_SHA, SECOND_SHA])
            ],
        },
    }


def update_attempt(status="processing", processed=0, failed=0, total=2, error="", captures=None, job_id="update-job"):
    return {
        "job_id": job_id, "snapshot_id": job_id + "-snapshot", "page_path": "fresh/about.html",
        "status": status, "error_message": error,
        "created_at": "2026-11-17T12:00:00Z", "completed_at": None,
        "progress": {"total": total, "processed": processed, "succeeded": processed - failed, "failed": failed},
        "captures": captures or [],
    }


def with_attempt(project, attempt):
    project["update_attempt"] = attempt
    return project


def failed_captures():
    return [
        {"commit_sha": FRESH_SHAS[0], "position": 0, "status": "complete", "error_message": ""},
        {"commit_sha": FRESH_SHAS[1], "position": 1, "status": "failed", "error_message": "Page did not load."},
    ]


def promoted_project():
    """What the backend returns once the new analysis becomes the displayed one."""
    project = saved_project(job_id="update-job", shas=FRESH_SHAS)
    project["analysis"]["page_path"] = "fresh/about.html"
    project["analysis"]["available_pages"] = ["index.html", "fresh/about.html"]
    return with_attempt(project, update_attempt(status="complete", processed=2, total=2))


def accepted_report():
    return {
        "overall_status": "accepted", "setup_available": True,
        "history": {"history_status": "passed", "reason": "History passed."},
        "html": {"html_status": "passed", "html_pages": ["index.html", "fresh/about.html"]},
        "dependencies": {"status": "passed", "reason": "Dependencies passed."},
    }


def fresh_commits():
    return {
        "commits": [
            {"sha": sha, "message": "Fresh commit " + str(index + 1), "date": "2026-11-17T10:00:00Z", "author_name": "Fresh author " + str(index + 1)}
            for index, sha in enumerate(FRESH_SHAS)
        ],
        "preselected": FRESH_SHAS[:],
    }


class UpdateReviewBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index = DIST / "index.html"
        sources = [path for path in (FRONTEND / "src").rglob("*") if path.suffix in (".js", ".jsx", ".css")]
        if not index.exists() or index.stat().st_mtime < max(path.stat().st_mtime for path in sources):
            raise unittest.SkipTest("Fresh Vite output is unavailable. Run the build and report any build failure separately.")
        print("Browser checks use fresh emitted assets; production-build success and html2canvas exports remain separate checks.", flush=True)
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch()
        except PlaywrightError as error:
            cls.playwright.stop()
            if "Executable doesn't exist" in str(error):
                raise unittest.SkipTest("Existing Playwright Chromium is unavailable; no browser will be installed.") from error
            raise

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.source = saved_project()
        self.other = saved_project("other-project", OTHER_URL, "Other project")
        self.report = accepted_report()
        self.history = fresh_commits()
        self.compatibility_status = 200
        self.network_failure = False
        self.hold_stage = None
        self.pending = []
        self.requests = []
        self.unexpected = []
        self.page_errors = []
        self.failed_requests = []
        self.allow_ordinary_submission = False
        self.created_payload = None
        self.created_project = None
        self.update_responses = []
        self.update_posts = []
        # Each project GET returns the next state; the last one repeats.
        self.source_states = []
        # The next N project reads fail with HTTP 503 (failed reads do not use up a scripted state).
        self.project_failures = 0
        self.context = self.browser.new_context(offline=True, service_workers="block", accept_downloads=True)
        self.context.route("**/*", self.handle_request)
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        self.page.on("requestfailed", lambda request: self.failed_requests.append(request))
        self.page.set_default_timeout(5000)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.unexpected, [], "Unexpected requests must never reach a backend.")
        self.assertEqual(self.page_errors, [])

    def respond(self, route, body, status=200):
        if isinstance(body, str):
            route.fulfill(status=status, content_type="application/json", body=body)
        else:
            route.fulfill(status=status, json=body)

    def handle_request(self, route):
        request = route.request
        address = urlsplit(request.url)
        path = address.path
        method = request.method

        # The document's font stylesheet is a known fixture, never fetched remotely.
        if address.hostname == "fonts.googleapis.com" and method == "GET":
            route.fulfill(content_type="text/css", body="")
            return
        if address.hostname != "us12.test":
            self.unexpected.append(method + " " + request.url)
            route.abort()
            return

        if path.startswith("/api/"):
            body = request.post_data_json if method == "POST" else None
            self.requests.append({"method": method, "path": path, "body": body})
            if path == "/api/analyses/":
                if method == "POST" and isinstance(body, dict) and "project_id" in body:
                    self.handle_update_post(route, body)
                elif method == "POST" and self.allow_ordinary_submission and self.created_payload is None:
                    self.created_payload = body
                    self.created_project = saved_project("mock-created-project", body["url"], body["name"])
                    self.respond(route, {"project_id": "mock-created-project", "job_id": "mock-created-job"}, 202)
                else:
                    self.unexpected.append("Forbidden analysis submission: " + str(body))
                    route.abort()
                return
            if method == "POST" and path in ("/api/repo/compatibility/", "/api/repo/commits/"):
                stage = "compatibility" if path.endswith("compatibility/") else "commits"
                response = self.report if stage == "compatibility" else self.history
                status = self.compatibility_status if stage == "compatibility" else 200
                if self.network_failure and stage == "compatibility":
                    route.abort()
                elif stage == self.hold_stage and body == {"url": SAVED_URL}:
                    self.hold_stage = None
                    self.pending.append((route, response, status))
                else:
                    self.respond(route, response, status)
                return
            if method == "POST" and path == "/api/repo/info/":
                self.respond(route, {"url": body["url"], "name": "Ordinary repository", "default_branch": "main"})
                return
            if method == "GET" and path == "/api/projects/saved-project/" and self.project_failures > 0:
                self.project_failures -= 1
                self.respond(route, {"error": self.PROJECT_UNAVAILABLE}, 503)
                return
            if method == "GET" and path in ("/api/projects/", "/api/projects/saved-project/"):
                self.advance_source()
            projects = [self.source, self.other]
            if self.created_project:
                projects.append(self.created_project)
            if method == "GET" and path == "/api/projects/":
                summaries = []
                for project in projects:
                    summaries.append({
                        "id": project["id"], "name": project["name"], "repository_url": project["repository_url"],
                        "job_id": project["analysis"]["job_id"],
                        "status": project["analysis"]["status"], "updated_at": "2026-11-16T10:01:00Z",
                        "progress": project["analysis"]["progress"], "thumbnail_url": None,
                        "update_attempt": project.get("update_attempt"),
                    })
                self.respond(route, {"projects": summaries})
                return
            for project in projects:
                if method == "GET" and path == f"/api/projects/{project['id']}/":
                    self.respond(route, project)
                    return
            if method == "GET" and re.fullmatch(r"/api/jobs/(saved-project|other-project|mock-created-project|update)-job/captures/[01]/image/", path):
                route.fulfill(content_type="image/png", body=PNG)
                return
            self.unexpected.append(method + " " + path)
            route.abort()
            return

        if method == "GET" and path in ("/", "/gallery", "/new-project", "/projects/saved-project/timeline", "/projects/other-project/timeline"):
            route.fulfill(path=str(DIST / "index.html"), content_type="text/html")
            return
        asset = (DIST / unquote(path).lstrip("/")).resolve()
        if method == "GET" and asset.is_relative_to(DIST.resolve()) and asset.is_file():
            route.fulfill(path=str(asset), content_type=mimetypes.guess_type(asset)[0] or "application/octet-stream")
            return
        self.unexpected.append(method + " " + path)
        route.abort()

    def handle_update_post(self, route, body):
        self.update_posts.append(body)
        if not self.update_responses:
            self.unexpected.append("Forbidden update submission: " + str(body))
            route.abort()
            return
        action = self.update_responses.pop(0)
        if action["kind"] == "network":
            route.abort()
        elif action["kind"] == "unreadable":
            route.fulfill(status=502, content_type="text/html", body="<html>Bad gateway</html>")
        elif action["kind"] == "hold":
            self.pending.append((route, action["body"], action["status"]))
        else:
            self.respond(route, action["body"], action["status"])

    def advance_source(self):
        if self.source_states:
            self.source = self.source_states[0]
            if len(self.source_states) > 1:
                self.source_states.pop(0)

    def project_reads(self):
        return len([r for r in self.requests if r["method"] == "GET" and r["path"] == "/api/projects/saved-project/"])

    def open_source(self):
        self.page.goto(ORIGIN + "/projects/saved-project/timeline")
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_visible()

    def test_timeline_hover_shows_the_current_commit_details(self):
        self.open_source()

        first = self.page.get_by_role("button", name=re.compile("^Select commit 1111111:"))
        second = self.page.get_by_role("button", name=re.compile("^Select commit 2222222:"))

        first.hover()
        first_info = self.page.locator("[role=tooltip]").filter(has_text="Saved commit 1")
        expect(first_info).to_have_css("opacity", "1")
        expect(first_info).to_contain_text("Saved author 1")
        expect(first_info).to_contain_text(FIRST_SHA[:7])
        expect(first_info).to_contain_text("11/16/26")

        second.hover()
        second_info = self.page.locator("[role=tooltip]").filter(has_text="Saved commit 2")
        expect(second_info).to_have_css("opacity", "1")
        expect(second_info).to_contain_text("Saved author 2")
        expect(second_info).to_contain_text(SECOND_SHA[:7])
        expect(second_info).to_contain_text("11/16/26")
        expect(first_info).to_have_css("opacity", "0")

    def open_review(self):
        self.page.get_by_role("button", name="Sync Updates", exact=True).click()
        expect(self.page.get_by_role("heading", name="Review update", exact=True)).to_be_visible()

    def wait_for_pending(self):
        deadline = time.monotonic() + 5
        while not self.pending and time.monotonic() < deadline:
            self.page.wait_for_timeout(20)
        self.assertTrue(self.pending, "The mocked request did not arrive.")

    def release_pending(self):
        route, body, status = self.pending.pop(0)
        try:
            self.respond(route, body, status)
        except PlaywrightError as error:
            if not any(word in str(error).lower() for word in ("cancel", "invalid interception", "closed")):
                raise

    def assert_no_analysis_submission(self):
        self.assertFalse(any(request["path"] == "/api/analyses/" for request in self.requests))

    def test_review_cancel_preserves_standard_and_compare_state(self):
        original = json.dumps(self.source, sort_keys=True)
        for mode in ("Standard", "Compare"):
            with self.subTest(mode=mode):
                self.open_source()
                self.page.get_by_label("Switch HTML page", exact=True).select_option("saved/about.html")
                self.page.get_by_role("button", name=re.compile("^Select commit 1111111:")).click()
                if mode == "Compare":
                    self.page.get_by_role("button", name="Compare", exact=True).click()
                    self.page.get_by_role("button", name="Add Commit", exact=True).click()
                    self.page.get_by_role("button", name=re.compile("^Select commit 2222222:")).click()
                timeline = self.page.get_by_role("list", name="Commit timeline", exact=True)
                picks = timeline.locator("button[aria-pressed=true]").evaluate_all("buttons => buttons.map(button => button.getAttribute('aria-label'))")
                images = self.page.get_by_role("region", name="Selected commits", exact=True).locator("img").evaluate_all("images => images.map(image => image.src)")

                self.open_review()
                self.assertEqual(self.page.url, ORIGIN + "/projects/saved-project/timeline")
                expect(self.page.get_by_label("GitHub Repository URL", exact=True)).to_have_value(SAVED_URL)
                expect(self.page.get_by_label("Project Title", exact=True)).to_have_attribute("readonly", "")
                expect(self.page.get_by_label("HTML Page", exact=True).locator("option")).to_have_text(["index.html", "fresh/about.html"])
                expect(self.page.get_by_text("Fresh commit 1", exact=True)).to_be_visible()
                self.page.get_by_label("HTML Page", exact=True).select_option("fresh/about.html")
                for checkbox in self.page.get_by_role("checkbox").all():
                    checkbox.uncheck()
                # With nothing selected, Save update cannot be used.
                expect(self.page.get_by_role("button", name="Save update", exact=True)).to_be_disabled()
                expect(self.page.get_by_role("button", name="Save update", exact=True)).to_have_attribute("type", "submit")
                expect(self.page.get_by_role("button", name="Create project", exact=True)).to_have_count(0)
                expect(self.page.get_by_role("button", name="Change repository", exact=True)).to_have_count(0)
                self.page.get_by_label("Project Title", exact=True).press("Enter")
                self.page.locator("form").evaluate("form => form.requestSubmit()")
                self.assertTrue(self.page.locator("form").evaluate("form => !form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}))"))
                self.assert_no_analysis_submission()
                reads_before_cancel = self.project_reads()
                self.page.get_by_role("button", name="Cancel", exact=True).click()

                expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
                # Canceling before saving restores the page without reloading the project.
                self.assertEqual(self.project_reads(), reads_before_cancel)
                expect(self.page.get_by_role("button", name=mode, exact=True)).to_have_attribute("aria-pressed", "true")
                expect(self.page.get_by_label("Switch HTML page", exact=True)).to_have_value("saved/about.html")
                self.assertEqual(timeline.locator("button[aria-pressed=true]").evaluate_all("buttons => buttons.map(button => button.getAttribute('aria-label'))"), picks)
                self.assertEqual(self.page.get_by_role("region", name="Selected commits", exact=True).locator("img").evaluate_all("images => images.map(image => image.src)"), images)

                # Reopening fetches choices again; the canceled draft is gone.
                self.open_review()
                expect(self.page.get_by_label("HTML Page", exact=True)).to_have_value("index.html")
                self.assertTrue(all(checkbox.is_checked() for checkbox in self.page.get_by_role("checkbox").all()))
                self.page.get_by_role("button", name="Cancel", exact=True).click()
                self.page.get_by_role("button", name="Download PNG", exact=True).click()
                dialog = self.page.get_by_role("dialog", name="Download PNG", exact=True)
                expect(dialog.get_by_role("button", name="Timeline (project timeline page screenshot)", exact=True)).to_be_enabled()
                download_name = "Screenshot of commit" if mode == "Standard" else "Two commits side by side with commit info"
                with self.page.expect_download() as download:
                    dialog.get_by_role("button", name=download_name, exact=True).click()
                self.assertTrue(download.value.suggested_filename.endswith(".png"))
                self.assert_no_analysis_submission()
        self.assertEqual(json.dumps(self.source, sort_keys=True), original)

    def test_loading_blocks_duplicates_through_both_requests(self):
        self.hold_stage = "compatibility"
        self.open_source()
        sync = self.page.get_by_role("button", name="Sync Updates", exact=True)
        sync.evaluate("button => { button.click(); button.click(); }")
        self.wait_for_pending()
        expect(sync).to_be_disabled()
        expect(sync).to_have_attribute("aria-busy", "true")
        self.assertEqual(len([request for request in self.requests if request["path"] == "/api/repo/compatibility/"]), 1)
        self.hold_stage = "commits"
        self.release_pending()
        self.wait_for_pending()
        expect(sync).to_be_disabled()
        self.release_pending()
        expect(self.page.get_by_role("heading", name="Review update", exact=True)).to_be_visible()
        setup_requests = [request for request in self.requests if request["method"] == "POST"]
        self.assertEqual([request["path"] for request in setup_requests], ["/api/repo/compatibility/", "/api/repo/commits/"])
        self.assertTrue(all(request["body"] == {"url": SAVED_URL} for request in setup_requests))
        self.assert_no_analysis_submission()

    def test_failure_explanations_preserve_results_and_allow_retry(self):
        cases = [
            ("rejected", 200, "The history exceeds the 50-commit limit."),
            ("pending", 200, "Dependency inspection is unfinished."),
            ("unavailable", 502, "GitHub is limiting requests. Try again later."),
            ("malformed", 200, "incomplete or invalid"),
            ("unreadable", 200, "unreadable response"),
            ("network", 200, "Could not reach the server"),
            ("bad commits", 200, "incomplete or invalid"),
        ]
        for status, http_status, message in cases:
            with self.subTest(status=status):
                self.report = accepted_report()
                self.history = fresh_commits()
                self.network_failure = status == "network"
                self.compatibility_status = http_status
                if status in ("rejected", "pending", "unavailable"):
                    self.report["overall_status"] = status
                    self.report["setup_available"] = False
                    self.report["dependencies"] = {"status": status, "reason": message}
                elif status == "malformed":
                    self.report["setup_available"] = False
                elif status == "unreadable":
                    self.report = "not JSON"
                elif status == "bad commits":
                    self.history["preselected"] = ["missing"]
                self.open_source()
                self.page.get_by_role("button", name="Sync Updates", exact=True).click()
                expect(self.page.get_by_role("alert")).to_contain_text(message)
                expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
                expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_enabled()
                expect(self.page.get_by_role("region", name="Selected commits", exact=True).locator("img")).to_have_count(1)
                self.report = accepted_report()
                self.history = fresh_commits()
                self.network_failure = False
                self.compatibility_status = 200
                self.open_review()
                self.page.get_by_role("button", name="Cancel", exact=True).click()
                self.assert_no_analysis_submission()

    def check_navigation_abort(self, stage):
        self.hold_stage = stage
        self.open_source()
        self.page.get_by_role("button", name="Sync Updates", exact=True).click()
        self.wait_for_pending()
        self.page.get_by_role("link", name="Back to Gallery", exact=True).click()
        expect(self.page.get_by_role("heading", name="Gallery", exact=True)).to_be_visible()
        self.page.get_by_role("link", name="Open Other project", exact=True).click()
        expect(self.page.get_by_role("heading", name="Other project", exact=True)).to_be_visible()
        self.open_review()
        expect(self.page.get_by_label("GitHub Repository URL", exact=True)).to_have_value(OTHER_URL)
        self.release_pending()
        expect(self.page.get_by_label("GitHub Repository URL", exact=True)).to_have_value(OTHER_URL)
        self.assertTrue(any(
            request.url.endswith(f"/api/repo/{stage}/") and request.post_data_json == {"url": SAVED_URL}
            for request in self.failed_requests
        ), "Leaving the source project must abort its pending request.")
        self.assert_no_analysis_submission()

    def test_navigation_aborts_compatibility_and_ignores_its_late_response(self):
        self.check_navigation_abort("compatibility")

    def test_navigation_aborts_commits_and_ignores_their_late_response(self):
        self.check_navigation_abort("commits")

    def test_malformed_source_context_cannot_fall_through_to_creation(self):
        self.source["analysis"]["job_id"] = ""
        self.open_source()
        self.page.get_by_role("button", name="Sync Updates", exact=True).click()
        expect(self.page.get_by_role("alert")).to_contain_text("Update review could not be opened")
        expect(self.page.get_by_role("button", name="Create project", exact=True)).to_have_count(0)
        expect(self.page.locator("form")).to_have_count(0)
        self.page.get_by_role("button", name="Cancel", exact=True).click()
        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
        self.assert_no_analysis_submission()


    # ---- Saving an update ----

    def save_update(self):
        self.page.get_by_role("button", name="Save update", exact=True).click()

    def wait_until(self, condition):
        deadline = time.monotonic() + 5
        while not condition() and time.monotonic() < deadline:
            self.page.wait_for_timeout(20)
        self.assertTrue(condition())

    def test_save_sends_the_exact_payload_and_replaces_results_only_when_the_backend_promotes(self):
        self.update_responses = [reply(202, ACCEPTED)]
        self.open_source()
        # Compare mode and a second pick must reset when the displayed analysis changes.
        self.page.get_by_role("button", name=re.compile("^Select commit 1111111:")).click()
        self.page.get_by_role("button", name="Compare", exact=True).click()
        self.page.get_by_role("button", name="Add Commit", exact=True).click()
        self.page.get_by_role("button", name=re.compile("^Select commit 2222222:")).click()
        self.open_review()
        self.page.get_by_label("HTML Page", exact=True).select_option("fresh/about.html")
        self.page.get_by_role("checkbox").first.uncheck()
        self.source_states = [
            with_attempt(saved_project(), update_attempt("queued")),
            with_attempt(saved_project(), update_attempt("processing", processed=1)),
            promoted_project(),
        ]
        self.save_update()

        # The route and project stay the same, and the old results remain usable.
        expect(self.page.get_by_text(re.compile("Update queued"))).to_be_visible()
        self.assertEqual(self.page.url, ORIGIN + "/projects/saved-project/timeline")
        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
        images = self.page.get_by_role("region", name="Selected commits", exact=True).locator("img")
        expect(images).to_have_count(2)
        expect(images.first).to_have_attribute("src", re.compile("saved-project-job"))
        expect(self.page.get_by_role("button", name="Download PNG", exact=True)).to_be_enabled()
        sync = self.page.get_by_role("button", name="Sync Updates", exact=True)
        expect(sync).to_be_disabled()
        # An update that is really processing is loading: busy flag and spinning icon.
        expect(sync).to_have_attribute("aria-busy", "true")
        expect(sync.locator("svg")).to_have_class(re.compile("spinning"))
        expect(self.page.get_by_text(re.compile("Update in progress — 1 / 2 processed"))).to_be_visible()
        expect(images.first).to_have_attribute("src", re.compile("saved-project-job"))

        # The backend promotes the new analysis: results, mode and selection are replaced.
        expect(self.page.get_by_text(re.compile("Project updated"))).to_be_visible()
        expect(self.page.get_by_role("button", name=re.compile("^Select commit aaaaaaa:"))).to_be_visible()
        expect(self.page.get_by_role("button", name=re.compile("^Select commit 1111111:"))).to_have_count(0)
        expect(self.page.get_by_role("button", name="Standard", exact=True)).to_have_attribute("aria-pressed", "true")
        expect(self.page.get_by_label("Switch HTML page", exact=True)).to_have_value("fresh/about.html")
        expect(self.page.get_by_text("Update in progress")).to_have_count(0)
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_enabled()
        self.assertEqual(self.update_posts, [{
            "url": SAVED_URL, "name": "Saved project", "page_path": "fresh/about.html",
            "commit_shas": [FRESH_SHAS[1]], "project_id": "saved-project", "source_job_id": "saved-project-job",
        }])
        self.assertEqual(self.page.url, ORIGIN + "/projects/saved-project/timeline")

        # Polling stops once the update is finished.
        reads = self.project_reads()
        self.page.wait_for_timeout(2600)
        self.assertEqual(self.project_reads(), reads)

    def test_clicks_and_enter_send_one_request_and_lock_the_review(self):
        self.update_responses = [hold(202, ACCEPTED)]
        self.open_source()
        self.open_review()
        self.source_states = [with_attempt(saved_project(), update_attempt("queued"))]
        save = self.page.get_by_role("button", name="Save update", exact=True)
        save.evaluate("button => { button.click(); button.click(); }")
        self.page.locator("form").evaluate("form => form.requestSubmit()")
        self.wait_for_pending()

        expect(self.page.get_by_role("button", name="Saving update", exact=True)).to_have_attribute("aria-busy", "true")
        expect(self.page.get_by_role("button", name="Cancel", exact=True)).to_be_disabled()
        expect(self.page.get_by_label("HTML Page", exact=True)).to_be_disabled()
        expect(self.page.get_by_text("does not cancel an update the server has already accepted")).to_be_visible()
        self.page.get_by_label("Project Title", exact=True).press("Enter")
        first_box = self.page.get_by_role("checkbox").first
        first_box.click()
        expect(first_box).to_be_checked()
        self.assertEqual(len(self.update_posts), 1)

        self.release_pending()
        expect(self.page.get_by_text(re.compile("Update queued"))).to_be_visible()
        self.assertEqual(len(self.update_posts), 1)

    def test_clear_refusals_keep_the_review_and_selections_without_retrying(self):
        cases = [
            (400, {"error": "Select between 1 and 10 commits."}, "Select between 1 and 10 commits."),
            (409, {"error": "The saved analysis has changed. Reload the project before updating it."}, "saved analysis has changed"),
            (404, {"error": "Project not found."}, "Project not found."),
        ]
        for status, body, message in cases:
            with self.subTest(status=status):
                self.update_posts = []
                self.update_responses = [reply(status, body)]
                self.open_source()
                self.open_review()
                self.page.get_by_label("HTML Page", exact=True).select_option("fresh/about.html")
                self.page.get_by_role("checkbox").first.uncheck()
                self.save_update()

                expect(self.page.get_by_role("alert").filter(has_text=message)).to_be_visible()
                expect(self.page.get_by_role("heading", name="Review update", exact=True)).to_be_visible()
                expect(self.page.get_by_label("HTML Page", exact=True)).to_have_value("fresh/about.html")
                expect(self.page.get_by_role("checkbox").first).not_to_be_checked()
                expect(self.page.get_by_role("checkbox").nth(1)).to_be_checked()
                expect(self.page.get_by_role("button", name="Save update", exact=True)).to_be_enabled()
                expect(self.page.get_by_role("button", name="Cancel", exact=True)).to_be_enabled()
                self.page.wait_for_timeout(600)
                self.assertEqual(len(self.update_posts), 1, "A refused update must not be retried automatically.")

                reads = self.project_reads()
                self.page.get_by_role("button", name="Cancel", exact=True).click()
                expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
                expect(self.page.get_by_role("region", name="Selected commits", exact=True).locator("img")).to_have_count(1)
                # After a request was sent, leaving the review reloads the project's current state.
                self.wait_until(lambda: self.project_reads() > reads)

    def test_user_can_resubmit_by_hand_after_a_clear_refusal(self):
        self.update_responses = [
            reply(400, {"error": "Select between 1 and 10 commits."}),
            reply(202, ACCEPTED),
        ]
        self.open_source()
        self.open_review()
        self.source_states = [with_attempt(saved_project(), update_attempt("queued"))]
        self.save_update()
        expect(self.page.get_by_role("alert").filter(has_text="Select between")).to_be_visible()
        self.assertEqual(len(self.update_posts), 1)
        self.save_update()
        expect(self.page.get_by_text(re.compile("Update queued"))).to_be_visible()
        self.assertEqual(len(self.update_posts), 2)

    # ---- Unknown outcomes ----

    UNKNOWN_ACTIONS = {
        "network failure": {"kind": "network"},
        "server error": reply(500, {"error": "Server error."}),
        "unreadable reply": {"kind": "unreadable"},
        "accepted for another project": reply(202, {**ACCEPTED, "project_id": "another-project"}),
    }

    def reach_unconfirmed_review(self, action):
        self.update_responses = [action]
        self.open_source()
        self.open_review()
        self.page.get_by_label("HTML Page", exact=True).select_option("fresh/about.html")
        self.save_update()
        expect(self.page.get_by_role("alert").filter(has_text="confirm whether the update was started")).to_be_visible()

    def test_unknown_outcomes_never_allow_resubmission(self):
        for name, action in self.UNKNOWN_ACTIONS.items():
            with self.subTest(name=name):
                self.update_posts = []
                self.reach_unconfirmed_review(action)
                expect(self.page.get_by_role("button", name="Save update", exact=True)).to_have_count(0)
                expect(self.page.get_by_role("button", name="Check again", exact=True)).to_be_enabled()
                expect(self.page.get_by_role("button", name="Back to project", exact=True)).to_be_enabled()
                expect(self.page.get_by_label("HTML Page", exact=True)).to_be_disabled()
                self.page.get_by_label("Project Title", exact=True).press("Enter")
                self.page.locator("form").evaluate("form => form.requestSubmit()")

                # Finding nothing is not treated as a failure or as permission to submit again.
                self.page.get_by_role("button", name="Check again", exact=True).click()
                expect(self.page.get_by_text("No new update is visible yet")).to_be_visible()
                expect(self.page.get_by_text("does not mean it failed")).to_be_visible()
                expect(self.page.get_by_role("button", name="Save update", exact=True)).to_have_count(0)
                self.page.wait_for_timeout(600)
                self.assertEqual(len(self.update_posts), 1)

    def test_unconfirmed_request_pauses_sync_and_keeps_results_usable(self):
        self.reach_unconfirmed_review(self.UNKNOWN_ACTIONS["network failure"])
        self.page.get_by_role("button", name="Back to project", exact=True).click()

        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
        notice = self.page.get_by_role("alert").filter(has_text="confirm your last update request")
        expect(notice).to_be_visible()
        sync = self.page.get_by_role("button", name="Sync Updates", exact=True)
        expect(sync).to_be_disabled()
        # Paused is not loading: no busy flag and no spinning icon.
        expect(sync).not_to_have_attribute("aria-busy", "true")
        expect(sync.locator("svg")).not_to_have_class(re.compile("spinning"))
        expect(self.page.get_by_role("region", name="Selected commits", exact=True).locator("img")).to_have_count(1)
        expect(self.page.get_by_role("button", name="Download PNG", exact=True)).to_be_enabled()
        self.page.get_by_role("button", name=re.compile("^Select commit 2222222:")).click()

        # Nothing visible: the notice stays and Sync stays paused.
        notice.get_by_role("button", name="Check again", exact=True).click()
        expect(notice).to_contain_text("No new update is visible yet")
        expect(sync).to_be_disabled()
        self.assertEqual(len(self.update_posts), 1)

        # A new attempt appears: it is shown with its real status and the pause ends.
        self.source_states = [with_attempt(saved_project(), update_attempt("failed", processed=2, failed=1, captures=failed_captures()))]
        notice.get_by_role("button", name="Check again", exact=True).click()
        expect(self.page.get_by_role("alert").filter(has_text="latest update failed")).to_be_visible()
        expect(self.page.get_by_text("confirm your last update request")).to_have_count(0)
        expect(sync).to_be_enabled()
        self.assertEqual(len(self.update_posts), 1)

    def test_reloading_loses_the_in_memory_pause(self):
        # This documents a known limit: only this page session remembers an unclear request.
        self.reach_unconfirmed_review(self.UNKNOWN_ACTIONS["server error"])
        self.page.get_by_role("button", name="Back to project", exact=True).click()
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_disabled()
        self.page.reload()
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_enabled()
        expect(self.page.get_by_text("confirm your last update request")).to_have_count(0)
        self.assertEqual(len(self.update_posts), 1)

    def check_found_attempt(self, found_project, expected_text, expect_promoted=False):
        self.reach_unconfirmed_review(self.UNKNOWN_ACTIONS["server error"])
        self.source_states = [found_project]
        self.page.get_by_role("button", name="Check again", exact=True).click()
        expect(self.page.get_by_role("heading", name="Review update", exact=True)).to_have_count(0)
        expect(self.page.get_by_text(expected_text).first).to_be_visible()
        expect(self.page.get_by_text("confirm your last update request")).to_have_count(0)
        if expect_promoted:
            expect(self.page.get_by_text(re.compile("Project updated"))).to_be_visible()
        else:
            expect(self.page.get_by_text(re.compile("Project updated"))).to_have_count(0)
        self.assertEqual(self.page.url, ORIGIN + "/projects/saved-project/timeline")
        self.assertEqual(len(self.update_posts), 1)

    def test_found_attempt_that_is_queued_is_labeled_queued(self):
        self.check_found_attempt(with_attempt(saved_project(), update_attempt("queued")), re.compile("Update queued"))

    def test_found_attempt_that_is_processing_is_labeled_in_progress(self):
        self.check_found_attempt(
            with_attempt(saved_project(), update_attempt("processing", processed=1)),
            re.compile("Update in progress — 1 / 2"),
        )
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_disabled()

    def test_found_attempt_that_already_failed_is_not_called_in_progress(self):
        failed = with_attempt(saved_project(), update_attempt("failed", processed=2, failed=2, error="The worker stopped."))
        self.check_found_attempt(failed, re.compile("latest update failed"))
        expect(self.page.get_by_text("Update in progress")).to_have_count(0)
        expect(self.page.get_by_text("The worker stopped.")).to_be_visible()
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_enabled()

    def test_found_attempt_that_is_partial_is_not_called_in_progress(self):
        partial = with_attempt(saved_project(), update_attempt("partially_complete", processed=2, failed=1, captures=failed_captures()))
        self.check_found_attempt(partial, re.compile("captured 1 of 2 selected commits"))
        expect(self.page.get_by_text("Update in progress")).to_have_count(0)
        expect(self.page.get_by_text("bbbbbbb: Page did not load.")).to_be_visible()

    def test_found_attempt_that_already_succeeded_shows_the_replacement(self):
        self.check_found_attempt(promoted_project(), re.compile("Project updated"), expect_promoted=True)
        expect(self.page.get_by_role("button", name=re.compile("^Select commit aaaaaaa:"))).to_be_visible()
        expect(self.page.get_by_text("Update in progress")).to_have_count(0)

    # ---- Candidate display ----

    def test_failed_and_partial_updates_explain_themselves_and_keep_old_results(self):
        cases = [
            ("failed", dict(processed=2, failed=2, error="The worker stopped."), "latest update failed", "The worker stopped."),
            ("partially_complete", dict(processed=2, failed=1, captures=failed_captures()), "captured 1 of 2", "bbbbbbb: Page did not load."),
            ("complete", dict(processed=2, failed=0), "without a complete set of screenshots", None),
        ]
        for status, fields, summary, detail in cases:
            with self.subTest(status=status):
                self.source = with_attempt(saved_project(), update_attempt(status, **fields))
                self.open_source()
                alert = self.page.get_by_role("alert").filter(has_text=summary)
                expect(alert).to_be_visible()
                expect(alert).to_contain_text("did not replace your results")
                expect(alert).to_contain_text("previous results are still shown")
                if detail:
                    expect(alert).to_contain_text(detail)
                expect(self.page.get_by_text("Update in progress")).to_have_count(0)
                images = self.page.get_by_role("region", name="Selected commits", exact=True).locator("img")
                expect(images).to_have_count(1)
                expect(images.first).to_have_attribute("src", re.compile("saved-project-job"))
                expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_enabled()
                expect(self.page.get_by_role("button", name="Download PNG", exact=True)).to_be_enabled()

    def test_polling_follows_a_candidate_while_the_displayed_analysis_is_complete(self):
        self.source_states = [
            with_attempt(saved_project(), update_attempt("queued")),
            with_attempt(saved_project(), update_attempt("processing", processed=1)),
            with_attempt(saved_project(), update_attempt("failed", processed=2, failed=2, error="The worker stopped.")),
        ]
        self.open_source()
        expect(self.page.get_by_text(re.compile("Update queued"))).to_be_visible()
        expect(self.page.get_by_text(re.compile("Update in progress — 1 / 2"))).to_be_visible(timeout=8000)
        expect(self.page.get_by_role("alert").filter(has_text="latest update failed")).to_be_visible(timeout=8000)
        expect(self.page.get_by_role("region", name="Selected commits", exact=True).locator("img").first).to_have_attribute("src", re.compile("saved-project-job"))
        reads = self.project_reads()
        self.page.wait_for_timeout(2600)
        self.assertEqual(self.project_reads(), reads, "Polling must stop at a terminal state.")

    def test_gallery_keeps_one_card_and_polls_the_candidate(self):
        processing = with_attempt(saved_project(), update_attempt("processing", processed=1))
        self.source_states = [processing, processing, promoted_project()]
        self.page.goto(ORIGIN + "/gallery")
        expect(self.page.get_by_text(re.compile("Update in progress — 1 / 2 processed"))).to_be_visible()
        expect(self.page.get_by_text("showing previous results")).to_be_visible()
        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_have_count(1)
        expect(self.page.get_by_role("heading", name="Other project", exact=True)).to_have_count(1)

        expect(self.page.get_by_text("Update in progress")).to_have_count(0, timeout=9000)
        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_have_count(1)
        expect(self.page.get_by_text("Latest update did not replace")).to_have_count(0)
        reads = len([r for r in self.requests if r["path"] == "/api/projects/"])
        self.page.wait_for_timeout(2600)
        self.assertEqual(len([r for r in self.requests if r["path"] == "/api/projects/"]), reads)

    def test_gallery_notes_a_failed_update_without_replacing_the_card(self):
        self.source = with_attempt(saved_project(), update_attempt("failed", processed=2, failed=2))
        self.page.goto(ORIGIN + "/gallery")
        expect(self.page.get_by_text("Latest update did not replace these results.")).to_be_visible()
        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_have_count(1)
        expect(self.page.get_by_text("Update in progress")).to_have_count(0)

    # ---- Navigating away while saving ----

    def test_leaving_while_saving_stops_waiting_but_cannot_cancel_an_accepted_update(self):
        self.update_responses = [hold(202, ACCEPTED)]
        self.page.goto(ORIGIN + "/gallery")
        self.page.get_by_role("link", name="Open Saved project", exact=True).click()
        self.open_review()
        self.save_update()
        self.wait_for_pending()

        self.page.go_back()
        expect(self.page.get_by_role("heading", name="Gallery", exact=True)).to_be_visible()
        # Leaving must stop waiting for the pending request (the event can arrive slightly later).
        self.wait_until(lambda: any(
            request.url.endswith("/api/analyses/") for request in self.failed_requests
        ))

        # Suppose the server had accepted it: reopening shows the candidate and blocks a second one.
        self.source = with_attempt(saved_project(), update_attempt("queued"))
        self.page.get_by_role("link", name="Open Saved project", exact=True).click()
        expect(self.page.get_by_text(re.compile("Update queued"))).to_be_visible()
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_disabled()
        self.release_pending()  # a late reply must be ignored
        self.assertEqual(len(self.update_posts), 1)
        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()

    # ---- Failed project refreshes keep the loaded page ----

    PROJECT_UNAVAILABLE = "Project service is temporarily unavailable."

    def load_error_alert(self):
        alert = self.page.get_by_role("alert").filter(has_text=self.PROJECT_UNAVAILABLE)
        expect(alert).to_be_visible()
        expect(alert).to_contain_text("does not submit another update")
        return alert

    def timeline_picks(self):
        timeline = self.page.get_by_role("list", name="Commit timeline", exact=True)
        return timeline.locator("button[aria-pressed=true]").evaluate_all("buttons => buttons.map(b => b.getAttribute('aria-label'))")

    def screenshots_decoded(self):
        images = self.page.get_by_role("region", name="Selected commits", exact=True).locator("img")
        return images.evaluate_all("images => images.length > 0 && images.every(i => i.complete && i.naturalWidth > 0)")

    def test_failed_refresh_after_an_accepted_update_keeps_the_timeline_and_retry_recovers(self):
        self.update_responses = [reply(202, ACCEPTED)]
        self.open_source()
        self.page.evaluate("window.__sameDocument = true")   # a full page reload would erase this
        self.page.get_by_role("button", name=re.compile("^Select commit 1111111:")).click()
        self.page.get_by_role("button", name="Compare", exact=True).click()
        self.page.get_by_role("button", name="Add Commit", exact=True).click()
        self.page.get_by_role("button", name=re.compile("^Select commit 2222222:")).click()
        picks = self.timeline_picks()
        self.open_review()
        self.project_failures = 1   # the refresh right after the update is accepted fails
        self.source_states = [
            with_attempt(saved_project(), update_attempt("queued")),
            with_attempt(saved_project(), update_attempt("processing", processed=1)),
            promoted_project(),
        ]
        self.save_update()

        # The loaded timeline stays, with a nonblocking error and an in-place Retry.
        alert = self.load_error_alert()
        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
        expect(self.page.get_by_role("button", name="Compare", exact=True)).to_have_attribute("aria-pressed", "true")
        self.assertEqual(self.timeline_picks(), picks)
        expect(self.page.get_by_role("region", name="Selected commits", exact=True).locator("img")).to_have_count(2)
        self.assertTrue(self.screenshots_decoded())
        expect(self.page.get_by_role("button", name="Download PNG", exact=True)).to_be_enabled()
        sync = self.page.get_by_role("button", name="Sync Updates", exact=True)
        expect(sync).to_be_disabled()   # the page may be out of date, so Sync is paused...
        expect(sync).not_to_have_attribute("aria-busy", "true")   # ...but nothing is loading
        # No hidden retry loop: nothing more is requested until the user clicks Retry.
        reads = self.project_reads()
        self.page.wait_for_timeout(2600)
        self.assertEqual(self.project_reads(), reads)
        self.assertEqual(len(self.update_posts), 1)

        # Retry reloads project data only (same document, no new update) and polling resumes.
        alert.get_by_role("button", name="Retry", exact=True).click()
        expect(self.page.get_by_text(re.compile("Update queued"))).to_be_visible()
        expect(alert).to_have_count(0)
        self.assertEqual(self.timeline_picks(), picks)   # same active analysis: nothing is reset
        expect(self.page.get_by_role("button", name="Compare", exact=True)).to_have_attribute("aria-pressed", "true")
        expect(self.page.get_by_text(re.compile("Update in progress — 1 / 2"))).to_be_visible()
        expect(self.page.get_by_text(re.compile("Project updated"))).to_be_visible(timeout=9000)
        expect(self.page.get_by_role("button", name=re.compile("^Select commit aaaaaaa:"))).to_be_visible()
        expect(self.page.get_by_role("button", name="Standard", exact=True)).to_have_attribute("aria-pressed", "true")
        self.assertTrue(self.page.evaluate("window.__sameDocument === true"))
        self.assertEqual(len(self.update_posts), 1, "Recovery must never submit another update.")

    def test_polling_failure_keeps_old_results_usable_and_retry_resumes_polling(self):
        self.source = with_attempt(saved_project(), update_attempt("processing", processed=1))
        self.open_source()
        self.page.evaluate("window.__sameDocument = true")
        self.project_failures = 1   # the next poll, about two seconds later, fails
        alert = self.load_error_alert()

        # The last known results and progress stay on screen and usable.
        expect(self.page.get_by_text(re.compile("Update in progress — 1 / 2"))).to_be_visible()
        images = self.page.get_by_role("region", name="Selected commits", exact=True).locator("img")
        expect(images).to_have_count(1)
        expect(images.first).to_have_attribute("src", re.compile("saved-project-job"))
        self.assertTrue(self.screenshots_decoded())
        self.page.get_by_role("button", name=re.compile("^Select commit 1111111:")).click()
        expect(images.first).to_have_attribute("src", re.compile("captures/0/image"))
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_disabled()
        # The failed poll does not silently loop.
        reads = self.project_reads()
        self.page.wait_for_timeout(2600)
        self.assertEqual(self.project_reads(), reads)

        # Retry restarts the status checks, which continue until the backend promotes the update.
        self.source_states = [
            with_attempt(saved_project(), update_attempt("processing", processed=1)),
            promoted_project(),
        ]
        alert.get_by_role("button", name="Retry", exact=True).click()
        expect(alert).to_have_count(0)
        expect(self.page.get_by_role("button", name=re.compile("^Select commit aaaaaaa:"))).to_be_visible(timeout=9000)
        expect(self.page.get_by_role("button", name=re.compile("^Select commit 1111111:"))).to_have_count(0)
        expect(self.page.get_by_text("Update in progress")).to_have_count(0)
        self.assertTrue(self.page.evaluate("window.__sameDocument === true"))
        self.assert_no_analysis_submission()
        self.assertEqual(self.update_posts, [])
        reads = self.project_reads()
        self.page.wait_for_timeout(2600)
        self.assertEqual(self.project_reads(), reads, "Polling must stop once the update is finished.")

    def test_first_load_failure_still_replaces_the_page_with_the_existing_error(self):
        self.project_failures = 1
        self.page.goto(TIMELINE)
        expect(self.page.get_by_role("alert").filter(has_text=self.PROJECT_UNAVAILABLE)).to_be_visible()
        expect(self.page.get_by_role("region", name="Selected commits", exact=True)).to_have_count(0)
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_have_count(0)
        self.page.get_by_role("button", name="Retry", exact=True).click()   # the original treatment reloads the page
        expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
        self.assert_no_analysis_submission()

    def test_unconfirmed_pause_survives_a_failed_refresh_and_retry(self):
        self.reach_unconfirmed_review(self.UNKNOWN_ACTIONS["network failure"])
        self.project_failures = 1
        self.page.get_by_role("button", name="Back to project", exact=True).click()

        alert = self.load_error_alert()
        notice = self.page.get_by_role("alert").filter(has_text="confirm your last update request")
        expect(notice).to_be_visible()
        sync = self.page.get_by_role("button", name="Sync Updates", exact=True)
        expect(sync).to_be_disabled()
        self.assertTrue(self.screenshots_decoded())

        alert.get_by_role("button", name="Retry", exact=True).click()
        expect(alert).to_have_count(0)
        expect(notice).to_be_visible()   # nothing new was found, so the protection stays
        expect(sync).to_be_disabled()
        self.assertEqual(len(self.update_posts), 1, "Recovery must never submit another update.")

    def test_ordinary_new_project_can_still_submit_only_to_a_mock(self):
        self.allow_ordinary_submission = True
        ordinary_url = "https://github.com/example/ordinary-project"
        self.page.goto(ORIGIN + "/new-project")
        self.page.get_by_label("GitHub Repository URL", exact=True).fill(ordinary_url)
        self.page.get_by_role("button", name="Next", exact=True).click()
        expect(self.page.get_by_role("button", name="Create project", exact=True)).to_be_enabled()
        self.page.get_by_role("button", name="Change repository", exact=True).click()
        expect(self.page.get_by_label("GitHub Repository URL", exact=True)).to_have_value(ordinary_url)
        self.page.get_by_role("button", name="Next", exact=True).click()
        self.page.get_by_label("Project Title", exact=True).fill("Ordinary edited title")
        self.page.get_by_label("HTML Page", exact=True).select_option("fresh/about.html")
        self.page.get_by_role("checkbox").first.uncheck()
        self.page.get_by_role("button", name="Create project", exact=True).click()
        expect(self.page).to_have_url(ORIGIN + "/projects/mock-created-project/timeline")
        expect(self.page.get_by_role("heading", name="Ordinary edited title", exact=True)).to_be_visible()
        self.assertEqual(self.created_payload, {
            "url": ordinary_url, "name": "Ordinary edited title",
            "page_path": "fresh/about.html", "commit_shas": [FRESH_SHAS[1]],
        })
        self.assertEqual(len([request for request in self.requests if request["path"] == "/api/analyses/"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
