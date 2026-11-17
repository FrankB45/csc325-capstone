"""Run with backend/.venv/bin/python frontend/tests/test_update_review_browser.py.

Uses fresh Vite output and an offline browser. All assets and APIs are fulfilled
locally; no server, database, worker, or real analysis is involved. A failed build
may emit usable assets: these checks do not certify a successful production build
or exercise timeline PNG exports that require html2canvas.
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
SAVED_URL = "https://github.com/example/saved-project"
OTHER_URL = "https://github.com/example/other-project"
FIRST_SHA = "1" * 40
SECOND_SHA = "2" * 40
FRESH_SHAS = ["a" * 40, "b" * 40]
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aK1sAAAAASUVORK5CYII="
)


def saved_project(project_id="saved-project", url=SAVED_URL, name="Saved project"):
    return {
        "id": project_id, "name": name, "repository_url": url,
        "analysis": {
            "job_id": project_id + "-job", "snapshot_id": project_id + "-snapshot",
            "page_path": "index.html", "default_page": "index.html",
            "available_pages": ["index.html", "saved/about.html"],
            "status": "complete", "error_message": "",
            "created_at": "2026-11-16T10:00:00Z", "completed_at": "2026-11-16T10:01:00Z",
            "progress": {"total": 2, "processed": 2, "succeeded": 2, "failed": 0},
            "commits": [
                {
                    "sha": sha, "message": "Saved commit " + str(index + 1),
                    "date": "2026-11-16T10:00:00Z", "status": "complete",
                    "error_message": "", "position": index,
                    "screenshot_url": f"/api/jobs/{project_id}-job/captures/{index}/image/",
                }
                for index, sha in enumerate([FIRST_SHA, SECOND_SHA])
            ],
        },
    }


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
            {"sha": sha, "message": "Fresh commit " + str(index + 1), "date": "2026-11-17T10:00:00Z"}
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
                if method == "POST" and self.allow_ordinary_submission and self.created_payload is None:
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
            projects = [self.source, self.other]
            if self.created_project:
                projects.append(self.created_project)
            if method == "GET" and path == "/api/projects/":
                summaries = []
                for project in projects:
                    summaries.append({
                        "id": project["id"], "name": project["name"], "repository_url": project["repository_url"],
                        "status": "complete", "updated_at": "2026-11-16T10:01:00Z",
                        "progress": project["analysis"]["progress"], "thumbnail_url": None,
                    })
                self.respond(route, {"projects": summaries})
                return
            for project in projects:
                if method == "GET" and path == f"/api/projects/{project['id']}/":
                    self.respond(route, project)
                    return
            if method == "GET" and re.fullmatch(r"/api/jobs/(saved-project|other-project|mock-created-project)-job/captures/[01]/image/", path):
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

    def open_source(self):
        self.page.goto(ORIGIN + "/projects/saved-project/timeline")
        expect(self.page.get_by_role("button", name="Sync Updates", exact=True)).to_be_visible()

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
                expect(self.page.get_by_role("button", name="Save update", exact=True)).to_be_disabled()
                expect(self.page.get_by_role("button", name="Save update", exact=True)).to_have_attribute("type", "button")
                expect(self.page.get_by_role("button", name="Create project", exact=True)).to_have_count(0)
                expect(self.page.get_by_role("button", name="Change repository", exact=True)).to_have_count(0)
                self.page.get_by_label("Project Title", exact=True).press("Enter")
                self.page.locator("form").evaluate("form => form.requestSubmit()")
                self.assertTrue(self.page.locator("form").evaluate("form => !form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}))"))
                self.assert_no_analysis_submission()
                self.page.get_by_role("button", name="Cancel", exact=True).click()

                expect(self.page.get_by_role("heading", name="Saved project", exact=True)).to_be_visible()
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
