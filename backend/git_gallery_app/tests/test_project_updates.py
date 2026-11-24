"""US-12 backend replacement tests; no frontend submission or history UI.

The group requested one visible project with replacement after full success.
Issue #12 still describes a distinct gallery analysis without replacement.
Retained records do not provide user-accessible history or satisfy that wording.
"""

import base64
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bson import ObjectId
from django.db import connection
from django.test import override_settings
from django.utils import timezone
import requests
from rest_framework.test import APITransactionTestCase

from ..models import Capture, Commit, Job, Project, RepositorySnapshot
from ..services import analyses
from ..services.jobs import create_job


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aK1sAAAAASUVORK5CYII="
)


class ProjectUpdateTests(APITransactionTestCase):
    def setUp(self):
        # Block the hardcoded collection before checking and redirecting test storage.
        storage_patch = patch.object(analyses, "_collection", object())
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        self.assertEqual(connection.settings_dict["NAME"], "test_git_gallery")
        self.database = connection.database
        self.assertEqual(self.database.name, "test_git_gallery")
        analyses._collection = self.database["analyses"]
        self.addCleanup(analyses._collection.drop)

        folder = TemporaryDirectory(prefix="us12-screenshots-")
        self.addCleanup(folder.cleanup)
        self.screenshot_root = Path(folder.name)
        screenshot_settings = override_settings(SCREENSHOT_ROOT=self.screenshot_root)
        screenshot_settings.enable()
        self.addCleanup(screenshot_settings.disable)

        # No test may accidentally reach GitHub or start the real capture child.
        network_patch = patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("Unexpected external request."),
        )
        network_patch.start()
        self.addCleanup(network_patch.stop)
        capture_patch = patch(
            "git_gallery_app.services.worker.subprocess.run",
            side_effect=AssertionError("A real capture must not run."),
        )
        capture_patch.start()
        self.addCleanup(capture_patch.stop)

        self.repo_url = "https://github.com/example/saved-project"
        self.old_shas = ["1" * 40, "2" * 40]
        self.fresh_shas = ["a" * 40, "b" * 40]
        self.project = Project.objects.create(name="Saved title", repository_url=self.repo_url)
        self.original_snapshot = RepositorySnapshot.objects.create(
            project=self.project,
            repository_url=self.repo_url,
            default_branch="main",
            head_sha=self.old_shas[-1],
            commits=[
                Commit(
                    sha=sha, message="Original commit", author_name="Test author",
                    committed_at=timezone.now(), position=position,
                )
                for position, sha in enumerate(self.old_shas)
            ],
            available_pages=["index.html"],
            default_page="index.html",
        )
        self.original_job = create_job(self.original_snapshot, "index.html", self.old_shas)
        self.set_outcome(self.original_job, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
        self.original_documents = self.stored_documents()
        self.original_details, self.original_summary = self.project_responses()

        github_results = {
            "get_repository_information": {
                "url": self.repo_url, "name": "Different GitHub title", "default_branch": "main",
            },
            "get_branch_revision": {"head_sha": self.fresh_shas[-1], "tree_sha": "f" * 40},
            "get_commit_history": [
                {
                    "sha": sha, "message": "Fresh commit", "author_name": "Test author",
                    "date": "2026-11-17T12:00:00Z",
                }
                for sha in self.fresh_shas
            ],
            "get_commit_file_changes": {},
            "get_commit_shas_for_path": set(),
            "_list_html_page_paths": ["index.html", "about.html"],
            "check_repository_dependencies": {"dependency_status": "passed", "reason": "Supported."},
        }
        self.github_mocks = {}
        for function_name, result in github_results.items():
            service_patch = patch(
                "git_gallery_app.services.analysis_setup." + function_name,
                return_value=result,
            )
            self.github_mocks[function_name] = service_patch.start()
            self.addCleanup(service_patch.stop)

    def stored_documents(self):
        return {
            name: list(self.database[name].find().sort("_id", 1))
            for name in ("projects", "repository_snapshots", "jobs", "analyses")
        }

    def update_payload(self, **changes):
        payload = {
            "url": "https://github.com/example/client-supplied-repository",
            "name": "Client-supplied title",
            "project_id": str(self.project.pk),
            "source_job_id": str(self.original_job.pk),
            "page_path": "about.html",
            "commit_shas": self.fresh_shas,
        }
        payload.update(changes)
        return payload

    def submit_update(self, **changes):
        return self.client.post("/api/analyses/", self.update_payload(**changes), format="json")

    def create_candidate(self, **changes):
        response = self.submit_update(**changes)
        self.assertEqual(response.status_code, 202, response.data)
        return Job.objects.get(pk=ObjectId(response.data["job_id"]))

    def set_outcome(self, job, status, capture_statuses):
        job.status = status
        job.completed_at = timezone.now()
        job.error_message = ""
        for capture, capture_status in zip(job.captures, capture_statuses):
            capture.status = capture_status
            capture.completed_at = job.completed_at
            capture.screenshot_path = ""
            capture.error_message = ""
            if capture_status == Capture.Status.COMPLETE:
                capture.screenshot_path = f"{job.pk}/{capture.position:02d}.png"
                image = self.screenshot_root / capture.screenshot_path
                image.parent.mkdir(parents=True, exist_ok=True)
                image.write_bytes(PNG)
            elif capture_status == Capture.Status.FAILED:
                capture.error_message = "The selected page could not be captured."
        job.save()
        job.refresh_from_db()

    def project_responses(self):
        details = self.client.get(f"/api/projects/{self.project.pk}/")
        gallery = self.client.get("/api/projects/")
        self.assertEqual(details.status_code, 200)
        self.assertEqual(gallery.status_code, 200)
        summary = next(item for item in gallery.data["projects"] if item["id"] == str(self.project.pk))
        return details.data, summary

    def assert_active_job(self, job):
        details, summary = self.project_responses()
        self.assertEqual(details["analysis"]["job_id"], str(job.pk))
        self.assertEqual(summary["job_id"], str(job.pk))
        self.assertEqual(details["analysis"]["status"], job.status)
        self.assertEqual(summary["status"], job.status)
        self.assertEqual(details["analysis"]["page_path"], job.page_path)
        self.assertEqual(summary["page_path"], job.page_path)
        self.assertEqual(summary["progress"], details["analysis"]["progress"])
        self.assertEqual(summary["progress"]["total"], len(job.captures))
        self.assertEqual(details["update_attempt"], summary["update_attempt"])
        return details, summary

    def assert_original_preserved(self):
        for collection, documents in self.original_documents.items():
            for document in documents:
                self.assertEqual(
                    self.database[collection].find_one({"_id": document["_id"]}), document,
                )
        for capture in self.original_job.captures:
            self.assertEqual((self.screenshot_root / capture.screenshot_path).read_bytes(), PNG)
            response = self.client.get(
                f"/api/jobs/{self.original_job.pk}/captures/{capture.position}/image/",
            )
            self.assertEqual(response.status_code, 200)
            try:
                self.assertEqual(b"".join(response.streaming_content), PNG)
            finally:
                response.close()

    def test_update_ids_must_be_paired(self):
        before = self.stored_documents()
        for missing_field in ("project_id", "source_job_id"):
            with self.subTest(missing_field=missing_field):
                payload = self.update_payload()
                del payload[missing_field]
                response = self.client.post("/api/analyses/", payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(missing_field, response.data)
                self.assertEqual(self.stored_documents(), before)
        self.github_mocks["get_repository_information"].assert_not_called()

    def test_update_ids_must_be_valid_nonempty_object_ids(self):
        before = self.stored_documents()
        for field in ("project_id", "source_job_id"):
            for value in (None, "", "not-an-id", "z" * 24, [], {}):
                with self.subTest(field=field, value=value):
                    response = self.submit_update(**{field: value})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.data)
                    self.assertEqual(self.stored_documents(), before)
        self.github_mocks["get_repository_information"].assert_not_called()

    def test_candidate_uses_saved_identity_without_another_project(self):
        candidate = self.create_candidate(
            project_id=str(self.project.pk).upper(),
            source_job_id=str(self.original_job.pk).upper(),
        )
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(RepositorySnapshot.objects.count(), 2)
        self.assertEqual(Job.objects.count(), 2)
        self.assertEqual(candidate.repo_snapshot.project_id, self.project.pk)
        self.assertEqual(candidate.repo_snapshot.repository_url, self.repo_url)
        self.assertEqual(candidate.repo_snapshot.head_sha, self.fresh_shas[-1])
        self.assertEqual(candidate.page_path, "about.html")
        self.assertEqual([capture.commit_sha for capture in candidate.captures], self.fresh_shas)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Saved title")
        self.assertEqual(self.project.repository_url, self.repo_url)
        self.github_mocks["get_repository_information"].assert_called_once_with(self.repo_url)
        self.github_mocks["get_branch_revision"].assert_called_once_with(self.repo_url, "main")
        self.github_mocks["get_commit_history"].assert_called_once_with(
            self.repo_url, ref=self.fresh_shas[-1],
        )
        self.github_mocks["check_repository_dependencies"].assert_called_once_with(
            self.repo_url, tree_sha="f" * 40,
        )
        self.assert_original_preserved()

    def test_missing_project_and_unknown_source_do_not_persist_work(self):
        before = self.stored_documents()
        cases = [
            ({"project_id": str(ObjectId())}, 404, "Project not found"),
            ({"source_job_id": str(ObjectId())}, 409, "saved analysis has changed"),
        ]
        for changes, expected_status, explanation in cases:
            with self.subTest(changes=changes):
                response = self.submit_update(**changes)
                self.assertEqual(response.status_code, expected_status)
                self.assertIn(explanation, response.data["error"])
                self.assertEqual(self.stored_documents(), before)
        self.github_mocks["get_repository_information"].assert_not_called()

    def test_source_from_another_project_is_rejected(self):
        other = Project.objects.create(name="Other project", repository_url=self.repo_url)
        before = self.stored_documents()
        response = self.submit_update(project_id=str(other.pk))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.stored_documents(), before)
        self.github_mocks["get_repository_information"].assert_not_called()

    def test_stale_source_after_success_is_rejected(self):
        candidate = self.create_candidate()
        self.set_outcome(candidate, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
        before = self.stored_documents()
        response = self.submit_update()
        self.assertEqual(response.status_code, 409)
        self.assertIn("Reload", response.data["error"])
        self.assertEqual(self.stored_documents(), before)
        self.assert_active_job(candidate)

    def test_busy_queued_and_processing_attempts_reject_another_submission(self):
        candidate = self.create_candidate()
        self.github_mocks["get_repository_information"].reset_mock()
        for status in (Job.Status.QUEUED, Job.Status.PROCESSING):
            with self.subTest(status=status):
                candidate.status = status
                candidate.save(update_fields=["status"])
                before = self.stored_documents()
                response = self.submit_update()
                self.assertEqual(response.status_code, 409)
                self.assertIn("already being processed", response.data["error"])
                self.assertEqual(self.stored_documents(), before)
        self.github_mocks["get_repository_information"].assert_not_called()

    def test_busy_state_is_rechecked_after_github_validation(self):
        def another_submission_finishes_validation(*args, **kwargs):
            create_job(self.original_snapshot, "index.html", self.old_shas)
            return {"dependency_status": "passed"}

        self.github_mocks["check_repository_dependencies"].side_effect = another_submission_finishes_validation
        response = self.submit_update()
        self.assertEqual(response.status_code, 409)
        # Only the simulated competing request's job was added.
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(RepositorySnapshot.objects.count(), 1)
        self.assertEqual(Job.objects.count(), 2)
        self.assert_original_preserved()

    def test_stale_source_is_rechecked_after_github_validation(self):
        def another_update_completes(*args, **kwargs):
            job = create_job(self.original_snapshot, "index.html", self.old_shas)
            self.set_outcome(job, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
            return {"dependency_status": "passed"}

        self.github_mocks["check_repository_dependencies"].side_effect = another_update_completes
        response = self.submit_update()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(RepositorySnapshot.objects.count(), 1)
        self.assertEqual(Job.objects.count(), 2)
        self.assert_original_preserved()

    def test_invalid_page_and_commit_selections_do_not_persist_work(self):
        before = self.stored_documents()
        cases = [
            {"page_path": "missing.html"},
            {"commit_shas": []},
            {"commit_shas": [self.fresh_shas[0]] * 2},
            {"commit_shas": ["c" * 40]},
            {"commit_shas": [f"{number:040x}" for number in range(11)]},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                response = self.submit_update(**changes)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.stored_documents(), before)

    def test_current_repository_rejections_and_unavailability_do_not_persist_work(self):
        before = self.stored_documents()
        for status, http_status in (("rejected", 400), ("pending", 400), ("unavailable", 502)):
            with self.subTest(status=status):
                self.github_mocks["check_repository_dependencies"].return_value = {
                    "dependency_status": status, "reason": "Current dependencies could not pass.",
                }
                response = self.submit_update()
                self.assertEqual(response.status_code, http_status)
                self.assertIn("Current dependencies", response.data["error"])
                self.assertEqual(self.stored_documents(), before)

    def test_missing_root_homepage_does_not_persist_work(self):
        before = self.stored_documents()
        self.github_mocks["_list_html_page_paths"].return_value = ["about.html"]
        response = self.submit_update()
        self.assertEqual(response.status_code, 400)
        self.assertIn("root index.html", response.data["error"])
        self.assertEqual(self.stored_documents(), before)

    def test_current_history_failure_does_not_persist_work(self):
        before = self.stored_documents()
        self.github_mocks["get_commit_history"].side_effect = ValueError("Repository has more than 50 commits.")
        response = self.submit_update()
        self.assertEqual(response.status_code, 400)
        self.assertIn("50 commits", response.data["error"])
        self.assertEqual(self.stored_documents(), before)

    def test_github_connection_failure_does_not_persist_work(self):
        before = self.stored_documents()
        self.github_mocks["get_repository_information"].side_effect = requests.ConnectionError()
        response = self.submit_update()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.stored_documents(), before)

    def test_queued_and_processing_attempts_keep_old_results_active(self):
        candidate = self.create_candidate()
        for status in (Job.Status.QUEUED, Job.Status.PROCESSING):
            with self.subTest(status=status):
                candidate.status = status
                candidate.save(update_fields=["status"])
                details, summary = self.assert_active_job(self.original_job)
                self.assertEqual(details["analysis"], self.original_details["analysis"])
                self.assertEqual(summary["thumbnail_url"], self.original_summary["thumbnail_url"])
                self.assertEqual(summary["updated_at"], self.original_summary["updated_at"])
                self.assertEqual(details["update_attempt"]["job_id"], str(candidate.pk))
                self.assertEqual(details["update_attempt"]["status"], status)
                self.assertEqual(details["update_attempt"]["progress"]["processed"], 0)
                self.assert_original_preserved()

        self.set_outcome(candidate, Job.Status.PROCESSING, [Capture.Status.COMPLETE, Capture.Status.PROCESSING])
        details, summary = self.assert_active_job(self.original_job)
        self.assertEqual(details["update_attempt"]["progress"], {
            "total": 2, "processed": 1, "succeeded": 1, "failed": 0,
        })
        self.assertEqual(summary["thumbnail_url"], self.original_summary["thumbnail_url"])

    def test_partial_and_total_failure_preserve_active_results_and_report_errors(self):
        candidate = self.create_candidate()
        cases = [
            (Job.Status.PARTIALLY_COMPLETE, [Capture.Status.COMPLETE, Capture.Status.FAILED], 1),
            (Job.Status.FAILED, [Capture.Status.FAILED] * 2, 0),
        ]
        for status, captures, succeeded in cases:
            with self.subTest(status=status):
                self.set_outcome(candidate, status, captures)
                candidate.error_message = "Processing stopped." if status == Job.Status.FAILED else ""
                candidate.save(update_fields=["error_message"])
                details, summary = self.assert_active_job(self.original_job)
                self.assertEqual(details["analysis"], self.original_details["analysis"])
                self.assertEqual(summary["thumbnail_url"], self.original_summary["thumbnail_url"])
                attempt = details["update_attempt"]
                self.assertEqual(attempt["status"], status)
                self.assertEqual(attempt["error_message"], candidate.error_message)
                self.assertEqual(attempt["progress"], {
                    "total": 2, "processed": 2, "succeeded": succeeded, "failed": 2 - succeeded,
                })
                self.assertIn("could not be captured", attempt["captures"][-1]["error_message"])
                self.assert_original_preserved()

    def test_complete_success_activates_candidate_without_deleting_old_results(self):
        candidate = self.create_candidate()
        self.set_outcome(candidate, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
        details, summary = self.assert_active_job(candidate)
        self.assertEqual(details["analysis"]["snapshot_id"], str(candidate.repo_snapshot_id))
        self.assertEqual(details["analysis"]["available_pages"], ["index.html", "about.html"])
        self.assertEqual([commit["sha"] for commit in details["analysis"]["commits"]], self.fresh_shas)
        self.assertEqual(summary["thumbnail_url"], f"/api/jobs/{candidate.pk}/captures/1/image/")
        self.assertEqual(summary["updated_at"], candidate.completed_at)
        self.assertEqual(details["update_attempt"]["job_id"], str(candidate.pk))
        self.assertEqual(len(self.client.get("/api/projects/").data["projects"]), 1)
        self.assertEqual(RepositorySnapshot.objects.count(), 2)
        self.assertEqual(Job.objects.count(), 2)
        self.assert_original_preserved()

    def test_switching_html_page_reuses_saved_snapshot_and_commits(self):
        self.original_snapshot.available_pages = [
            "index.html",
            "pages/about.html",
            "work.html",
        ]
        self.original_snapshot.save(update_fields=["available_pages"])
        self.github_mocks["get_commit_shas_for_path"].side_effect = [
            {self.old_shas[1]},
            {self.old_shas[0]},
            set(),
        ]
        self.github_mocks["get_commit_file_changes"].side_effect = [
            {"pages/about.html": "modified"},
            {"index.html": "modified"},
        ]

        response = self.client.post(
            f"/api/jobs/{self.original_job.pk}/pages/",
            {"page_path": "pages/about.html"},
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)

        page_job = Job.objects.get(pk=ObjectId(response.data["job_id"]))
        self.assertEqual(page_job.repo_snapshot_id, self.original_snapshot.pk)
        self.assertEqual(page_job.page_path, "pages/about.html")
        self.assertEqual(
            [capture.commit_sha for capture in page_job.captures],
            [self.old_shas[1]],
        )

        self.set_outcome(
            page_job,
            Job.Status.COMPLETE,
            [Capture.Status.COMPLETE],
        )
        details = self.client.get(f"/api/projects/{self.project.pk}/").data
        self.assertEqual(details["analysis"]["job_id"], str(page_job.pk))
        self.assertEqual(details["analysis"]["page_path"], "pages/about.html")
        self.assertEqual(
            [commit["status"] for commit in details["analysis"]["commits"]],
            [Capture.Status.COMPLETE],
        )

        index_response = self.client.post(
            f"/api/jobs/{page_job.pk}/pages/",
            {"page_path": "index.html"},
            format="json",
        )
        self.assertEqual(index_response.status_code, 202, index_response.data)
        index_job = Job.objects.get(pk=ObjectId(index_response.data["job_id"]))
        self.assertEqual(
            [capture.commit_sha for capture in index_job.captures],
            [self.old_shas[0]],
        )
        self.set_outcome(index_job, Job.Status.COMPLETE, [Capture.Status.COMPLETE])

        no_changes = self.client.post(
            f"/api/jobs/{index_job.pk}/pages/",
            {"page_path": "work.html"},
            format="json",
        )
        self.assertEqual(no_changes.status_code, 400)
        self.assertIn("No selected commits changed", no_changes.data["error"])
        self.assertEqual(Job.objects.count(), 3)

    def test_page_switch_rejects_unavailable_pages_and_busy_projects(self):
        self.original_snapshot.available_pages = ["index.html", "about.html"]
        self.original_snapshot.save(update_fields=["available_pages"])
        before = Job.objects.count()

        missing_page = self.client.post(
            f"/api/jobs/{self.original_job.pk}/pages/",
            {"page_path": "missing.html"},
            format="json",
        )
        self.assertEqual(missing_page.status_code, 400)
        self.assertEqual(Job.objects.count(), before)

        create_job(self.original_snapshot, "about.html", self.old_shas)
        busy_response = self.client.post(
            f"/api/jobs/{self.original_job.pk}/pages/",
            {"page_path": "about.html"},
            format="json",
        )
        self.assertEqual(busy_response.status_code, 409)

    def test_page_switch_reports_github_lookup_failures(self):
        self.original_snapshot.available_pages = ["index.html", "about.html"]
        self.original_snapshot.save(update_fields=["available_pages"])
        self.github_mocks["get_commit_shas_for_path"].side_effect = requests.HTTPError(
            "GitHub rate limit exceeded."
        )

        response = self.client.post(
            f"/api/jobs/{self.original_job.pk}/pages/",
            {"page_path": "about.html"},
            format="json",
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("GitHub rate limit exceeded", response.data["error"])
        self.assertEqual(Job.objects.count(), 1)

    def test_repeated_updates_keep_the_latest_success_until_another_succeeds(self):
        first = self.create_candidate()
        self.set_outcome(first, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
        second = self.create_candidate(source_job_id=str(first.pk))
        self.set_outcome(second, Job.Status.FAILED, [Capture.Status.FAILED] * 2)
        self.assert_active_job(first)
        before = self.stored_documents()
        rejected = self.submit_update(source_job_id=str(second.pk))
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(self.stored_documents(), before)
        third = self.create_candidate(source_job_id=str(first.pk), commit_shas=[self.fresh_shas[0]])
        self.assert_active_job(first)
        self.set_outcome(third, Job.Status.COMPLETE, [Capture.Status.COMPLETE])
        details, summary = self.assert_active_job(third)
        self.assertEqual(summary["progress"]["total"], 1)
        self.assertEqual(details["update_attempt"]["job_id"], str(third.pk))
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(RepositorySnapshot.objects.count(), 4)
        self.assertEqual(Job.objects.count(), 4)
        self.assertTrue((self.screenshot_root / first.captures[0].screenshot_path).is_file())
        self.assert_original_preserved()

    def test_empty_incomplete_or_missing_path_captures_do_not_activate(self):
        candidate = self.create_candidate()
        for invalid_case in ("empty", "unfinished", "missing path"):
            with self.subTest(invalid_case=invalid_case):
                candidate.refresh_from_db()
                candidate.captures = [
                    Capture(commit_sha=sha, position=position, status=Capture.Status.COMPLETE,
                            screenshot_path=f"{candidate.pk}/{position:02d}.png")
                    for position, sha in enumerate(self.fresh_shas)
                ]
                candidate.status = Job.Status.COMPLETE
                if invalid_case == "empty":
                    candidate.captures = []
                elif invalid_case == "unfinished":
                    candidate.captures[-1].status = Capture.Status.PENDING
                else:
                    candidate.captures[-1].screenshot_path = ""
                candidate.save()
                self.assert_active_job(self.original_job)

    def test_all_captures_finished_without_complete_job_status_do_not_activate(self):
        candidate = self.create_candidate()
        self.set_outcome(candidate, Job.Status.PROCESSING, [Capture.Status.COMPLETE] * 2)
        self.assert_active_job(self.original_job)

    def test_tied_creation_times_and_out_of_order_completion_use_job_id(self):
        older = self.create_candidate()
        # Simulate two accepted requests racing; this deliberately bypasses the API busy check.
        newer = create_job(older.repo_snapshot, "about.html", self.fresh_shas)
        Job.objects.filter(pk=older.pk).update(created_at=newer.created_at)
        older.refresh_from_db()
        self.assertGreater(str(newer.pk), str(older.pk))
        self.set_outcome(newer, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
        self.assert_active_job(newer)
        self.set_outcome(older, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
        older.completed_at = newer.completed_at + timedelta(seconds=1)
        older.save(update_fields=["completed_at"])
        details, _ = self.assert_active_job(newer)
        self.assertGreater(older.completed_at, newer.completed_at)
        self.assertEqual(details["update_attempt"]["job_id"], str(newer.pk))

    def test_creation_time_takes_priority_over_job_id_and_completion_time(self):
        first = self.create_candidate()
        second = create_job(first.repo_snapshot, "about.html", self.fresh_shas)
        Job.objects.filter(pk=first.pk).update(created_at=second.created_at + timedelta(seconds=1))
        first.refresh_from_db()
        self.set_outcome(first, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
        self.set_outcome(second, Job.Status.COMPLETE, [Capture.Status.COMPLETE] * 2)
        details, _ = self.assert_active_job(first)
        self.assertEqual(details["update_attempt"]["job_id"], str(first.pk))

    def test_ordinary_creation_without_update_ids_still_creates_a_project(self):
        payload = self.update_payload()
        del payload["project_id"]
        del payload["source_job_id"]
        response = self.client.post("/api/analyses/", payload, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertNotEqual(response.data["project_id"], str(self.project.pk))
        created = Project.objects.get(pk=ObjectId(response.data["project_id"]))
        self.assertEqual(created.name, payload["name"])
        self.assertEqual(Project.objects.count(), 2)
        self.github_mocks["get_repository_information"].assert_called_once_with(payload["url"])
        details = self.client.get(f"/api/projects/{created.pk}/").data
        self.assertEqual(details["analysis"]["status"], Job.Status.QUEUED)
        self.assertIsNone(details["update_attempt"])
        self.assert_original_preserved()

    def test_initial_analysis_display_is_preserved_for_ordinary_projects(self):
        cases = [
            (Job.Status.QUEUED, [Capture.Status.PENDING] * 2),
            (Job.Status.PROCESSING, [Capture.Status.PROCESSING, Capture.Status.PENDING]),
            (Job.Status.PARTIALLY_COMPLETE, [Capture.Status.COMPLETE, Capture.Status.FAILED]),
            (Job.Status.FAILED, [Capture.Status.FAILED] * 2),
        ]
        for status, captures in cases:
            with self.subTest(status=status):
                self.set_outcome(self.original_job, status, captures)
                details, summary = self.assert_active_job(self.original_job)
                self.assertIsNone(details["update_attempt"])
                if status == Job.Status.PARTIALLY_COMPLETE:
                    self.assertEqual(summary["thumbnail_url"], f"/api/jobs/{self.original_job.pk}/captures/0/image/")
                else:
                    self.assertIsNone(summary["thumbnail_url"])

    def test_failed_updates_preserve_an_initial_failed_or_partial_analysis(self):
        cases = [
            (Job.Status.PARTIALLY_COMPLETE, [Capture.Status.COMPLETE, Capture.Status.FAILED]),
            (Job.Status.FAILED, [Capture.Status.FAILED] * 2),
        ]
        for status, captures in cases:
            with self.subTest(status=status):
                self.set_outcome(self.original_job, status, captures)
                candidate = self.create_candidate()
                self.assert_active_job(self.original_job)
                self.set_outcome(candidate, Job.Status.FAILED, [Capture.Status.FAILED] * 2)
                self.assert_active_job(self.original_job)

    def test_project_without_jobs_keeps_empty_details_and_summary(self):
        empty = Project.objects.create(name="No analysis", repository_url=self.repo_url)
        details = self.client.get(f"/api/projects/{empty.pk}/").data
        summaries = self.client.get("/api/projects/").data["projects"]
        summary = next(item for item in summaries if item["id"] == str(empty.pk))
        self.assertIsNone(details["analysis"])
        self.assertIsNone(details["update_attempt"])
        self.assertIsNone(summary["job_id"])
        self.assertIsNone(summary["update_attempt"])
