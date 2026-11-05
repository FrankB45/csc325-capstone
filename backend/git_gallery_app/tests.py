import json
from unittest import TestCase
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

# Create your tests here.

import unittest
from .commit_selection import SelectionError, default_selection, validate_selection


def shas(n):
    return [f"{i:040x}" for i in range(n)]


class DefaultSelectionTests(unittest.TestCase):
    def test_single_commit_selected_once(self):  # AC2
        h = shas(1)
        self.assertEqual(default_selection(h), h)

    def test_ten_or_fewer_selects_all(self):  # AC1
        for n in (2, 5, 10):
            self.assertEqual(default_selection(shas(n)), shas(n))

    def test_more_than_ten_picks_ten_distinct_with_ends(self):  # AC1
        for n in range(11, 51):
            h = shas(n)
            sel = default_selection(h)
            self.assertEqual(len(sel), 10, n)
            self.assertEqual(len(set(sel)), 10, n)
            self.assertEqual(sel[0], h[0])
            self.assertEqual(sel[-1], h[-1])
            self.assertEqual(sel, sorted(sel, key=h.index))  # stays in history order


class ValidateSelectionTests(unittest.TestCase):
    def test_empty_rejected(self):  # AC4
        with self.assertRaises(SelectionError) as c:
            validate_selection([], shas(5))
        self.assertEqual(c.exception.code, "selection_empty")

    def test_eleven_rejected(self):  # AC4
        with self.assertRaises(SelectionError) as c:
            validate_selection(shas(11), shas(20))
        self.assertEqual(c.exception.code, "selection_too_many")

    def test_unknown_and_duplicate_rejected(self):
        with self.assertRaises(SelectionError):
            validate_selection(["f" * 40], shas(5))
        with self.assertRaises(SelectionError):
            validate_selection([shas(5)[0]] * 2, shas(5))

    def test_boundaries_ok_and_ordered(self):
        h = shas(20)
        self.assertEqual(validate_selection([h[3]], h), [h[3]])
        self.assertEqual(validate_selection(list(reversed(h[:10])), h), h[:10])


if __name__ == "__main__":
    unittest.main()
from .services.github import check_repository_history, get_repository_information


class RepositoryHistoryTests(TestCase):
    def setUp(self):
        self.repo_url = "https://github.com/example/site"
        self.repository_data = {
            "name": "site",
            "full_name": "example/site",
            "description": "A static website",
            "default_branch": "main",
            "html_url": self.repo_url,
        }
        request_patch = patch("git_gallery_app.services.github.requests.get")
        self.mock_get = request_patch.start()
        self.addCleanup(request_patch.stop)
        self.mock_get.side_effect = AssertionError("Unexpected GitHub request.")

    def make_response(self, data, status_code=200, next_page=None):
        """Use a real Response so JSON, HTTP errors, and Link parsing are exercised."""
        response = requests.Response()
        response.status_code = status_code
        response.url = "https://api.github.com/repos/example/site/commits"
        response._content = json.dumps(data).encode("utf-8")
        if next_page is not None:
            response.headers["Link"] = (
                f'<{response.url}?sha=main&per_page=50&page={next_page}>; rel="next"'
            )
        return response

    def make_commits(self, count, start=1):
        return [{"sha": f"commit-{number}"} for number in range(start, start + count)]

    def check_history(self, *commit_responses):
        self.mock_get.side_effect = [
            self.make_response(self.repository_data),
            *commit_responses,
        ]
        return check_repository_history(self.repo_url)

    def test_missing_default_branch_is_rejected_without_requesting_commits(self):
        for default_branch in (None, "", "   "):
            with self.subTest(default_branch=default_branch):
                self.mock_get.reset_mock()
                self.repository_data["default_branch"] = default_branch
                result = self.check_history()

                self.assertEqual(result["history_status"], "rejected")
                self.assertIn("no usable default branch", result["reason"])
                self.assertEqual(self.mock_get.call_count, 1)

    def test_zero_commits_is_rejected(self):
        result = self.check_history(self.make_response([]))

        self.assertEqual(result["history_status"], "rejected")
        self.assertIn("no commits", result["reason"])

    def test_one_commit_passes_history_only(self):
        result = self.check_history(self.make_response(self.make_commits(1)))

        self.assertEqual(result["history_status"], "passed")
        self.assertEqual(result["commit_count"], 1)
        self.assertIn("HTML-page and unsupported-dependency checks", result["reason"])
        self.assertNotIn("compatible", result)

    def test_fifty_commits_without_a_next_page_passes(self):
        result = self.check_history(self.make_response(self.make_commits(50)))

        self.assertEqual(result["history_status"], "passed")
        self.assertEqual(result["commit_count"], 50)
        self.assertEqual(self.mock_get.call_count, 2)

    def test_fifty_one_commits_across_pages_is_rejected(self):
        result = self.check_history(
            self.make_response(self.make_commits(50), next_page=2),
            self.make_response(self.make_commits(1, start=51)),
        )

        self.assertEqual(result["history_status"], "rejected")
        self.assertIn("50-commit limit", result["reason"])
        self.assertEqual(self.mock_get.call_count, 3)
        # Rejected histories are not reported as having an exact total count.
        self.assertNotIn("commit_count", result)

    def test_fifty_commits_across_shorter_pages_passes(self):
        result = self.check_history(
            self.make_response(self.make_commits(30), next_page=2),
            self.make_response(self.make_commits(20, start=31)),
        )

        self.assertEqual(result["history_status"], "passed")
        self.assertEqual(result["commit_count"], 50)
        self.assertEqual(self.mock_get.call_count, 3)

    def test_fifty_one_commits_across_shorter_pages_is_rejected(self):
        result = self.check_history(
            self.make_response(self.make_commits(30), next_page=2),
            self.make_response(self.make_commits(21, start=31)),
        )

        self.assertEqual(result["history_status"], "rejected")
        self.assertIn("50-commit limit", result["reason"])

    def test_stops_requesting_pages_after_exceeding_limit(self):
        result = self.check_history(
            self.make_response(self.make_commits(50), next_page=2),
            self.make_response(self.make_commits(50, start=51), next_page=3),
        )

        self.assertEqual(result["history_status"], "rejected")
        self.assertEqual(self.mock_get.call_count, 3)

    def test_uses_default_branch_then_pins_later_pages_to_its_head_commit(self):
        self.repository_data["default_branch"] = "release/site"
        self.check_history(
            self.make_response(self.make_commits(30), next_page=2),
            self.make_response(self.make_commits(20, start=31)),
        )

        first_page = self.mock_get.call_args_list[1]
        second_page = self.mock_get.call_args_list[2]
        self.assertEqual(
            first_page.args, ("https://api.github.com/repos/example/site/commits",)
        )
        self.assertEqual(
            first_page.kwargs["params"],
            {"sha": "release/site", "per_page": 50, "page": 1},
        )
        self.assertEqual(
            second_page.kwargs["params"],
            {"sha": "commit-1", "per_page": 50, "page": 2},
        )
        self.assertEqual(second_page.args, first_page.args)
        self.assertEqual(first_page.kwargs["timeout"], 10)
        self.assertEqual(second_page.kwargs["timeout"], 10)

    def test_missing_default_branch_history_is_rejected(self):
        result = self.check_history(self.make_response({}, status_code=404))

        self.assertEqual(result["history_status"], "rejected")
        self.assertIn("Default-branch history was not found", result["reason"])

    def test_github_empty_repository_conflict_is_rejected(self):
        result = self.check_history(
            self.make_response({"message": "Git Repository is empty."}, status_code=409)
        )

        self.assertEqual(result["history_status"], "rejected")
        self.assertIn("no commits", result["reason"])

    def test_other_conflicts_are_upstream_failures(self):
        result = self.check_history(
            self.make_response({"message": "Another conflict"}, status_code=409)
        )

        self.assertEqual(result["history_status"], "unavailable")
        self.assertIn("Try again", result["reason"])

    def test_upstream_http_failures_do_not_reject_or_pass_history(self):
        for status_code in (401, 403, 422, 429, 500, 503):
            with self.subTest(status_code=status_code):
                result = self.check_history(self.make_response({}, status_code=status_code))

                self.assertEqual(result["history_status"], "unavailable")
                self.assertIn("Try again", result["reason"])

    def test_second_page_failure_does_not_pass_partial_history(self):
        result = self.check_history(
            self.make_response(self.make_commits(50), next_page=2),
            self.make_response({}, status_code=500),
        )

        self.assertEqual(result["history_status"], "unavailable")
        self.assertNotIn("commit_count", result)

    def test_timeout_and_connection_failure_are_unavailable(self):
        for error in (requests.Timeout(), requests.ConnectionError()):
            with self.subTest(error=type(error).__name__):
                result = self.check_history(error)

                self.assertEqual(result["history_status"], "unavailable")
                self.assertIn("Try again", result["reason"])

    def test_invalid_commit_json_is_unavailable(self):
        response = self.make_response([])
        response._content = b"not JSON"

        result = self.check_history(response)

        self.assertEqual(result["history_status"], "unavailable")

    def test_invalid_commit_payload_is_unavailable(self):
        for payload in ({"message": "Unexpected object"}, [None], [{}], [{"sha": ""}]):
            with self.subTest(payload=payload):
                result = self.check_history(self.make_response(payload))

                self.assertEqual(result["history_status"], "unavailable")

    def test_empty_page_with_next_link_is_unavailable(self):
        result = self.check_history(self.make_response([], next_page=2))

        self.assertEqual(result["history_status"], "unavailable")

    def test_repository_lookup_failures_are_handled(self):
        cases = ((404, "rejected"), (403, "unavailable"), (500, "unavailable"))
        for status_code, expected_status in cases:
            with self.subTest(status_code=status_code):
                self.mock_get.side_effect = [self.make_response({}, status_code=status_code)]

                result = check_repository_history(self.repo_url)

                self.assertEqual(result["history_status"], expected_status)

    def test_malformed_repository_information_is_unavailable(self):
        for payload in ({}, [], {**self.repository_data, "default_branch": 123}):
            with self.subTest(payload=payload):
                self.mock_get.side_effect = [self.make_response(payload)]

                result = check_repository_history(self.repo_url)

                self.assertEqual(result["history_status"], "unavailable")

    def test_invalid_repository_json_is_unavailable(self):
        response = self.make_response({})
        response._content = b"not JSON"
        self.mock_get.side_effect = [response]

        result = check_repository_history(self.repo_url)

        self.assertEqual(result["history_status"], "unavailable")

    def test_invalid_url_is_rejected_before_any_github_request(self):
        result = check_repository_history("https://example.com/owner/repo")

        self.assertEqual(result["history_status"], "rejected")
        self.assertIn("GitHub URL", result["reason"])
        self.mock_get.assert_not_called()

    def test_existing_repository_information_result_is_preserved(self):
        self.mock_get.side_effect = [self.make_response(self.repository_data)]

        result = get_repository_information(self.repo_url)

        self.assertEqual(result, {
            "name": "site",
            "full_name": "example/site",
            "description": "A static website",
            "default_branch": "main",
            "url": self.repo_url,
        })
        self.assertEqual(self.mock_get.call_count, 1)


class GitGalleryAppTests(SimpleTestCase):
    def test_example(self):
        self.assertTrue(True)
from django.test import TransactionTestCase
from django.utils import timezone

from .models import Project, RepositorySnapshot, Commit, Job, Capture
from .services.jobs import create_job, claim_next_job

from datetime import timedelta

from unittest.mock import Mock

from .services.processing import process_job



##########
# Tests for the Job functionality

class JobTests(TransactionTestCase):
    def setUp(self):
        project = Project.objects.create(
            name="Test project",
            repository_url="https://github.com/example/demo",
        )

        # Eleven distinct, synthetic commit SHAs.
        self.shas = [f"{number:040x}" for number in range(1, 12)]

        self.snapshot = RepositorySnapshot.objects.create(
            project=project,
            repository_url=project.repository_url,
            default_branch="main",
            head_sha=self.shas[-1],
            commits=[
                Commit(
                    sha=sha,
                    message=f"Commit {position}",
                    author_name="Test Author",
                    committed_at=timezone.now(),
                    position=position,
                )
                for position, sha in enumerate(self.shas)
            ],
            available_pages=["index.html", "about.html"],
            default_page="index.html",
        )

        # Use the snapshot as loaded from MongoDB.
        self.snapshot.refresh_from_db()

##########
# Tests for the create_job function

    def test_saves_job_in_history_order(self):
        job = create_job(
            self.snapshot,
            "about.html",
            [self.shas[8], self.shas[2], self.shas[5]],
        )

        saved_job = Job.objects.get(pk=job.pk)

        self.assertEqual(saved_job.repo_snapshot_id, self.snapshot.pk)
        self.assertEqual(saved_job.page_path, "about.html")
        self.assertEqual(saved_job.status, Job.Status.QUEUED)

        self.assertEqual(
            [capture.commit_sha for capture in saved_job.captures],
            [self.shas[2], self.shas[5], self.shas[8]],
        )

        self.assertEqual(
            [capture.position for capture in saved_job.captures],
            [0, 1, 2],
        )

        for capture in saved_job.captures:
            self.assertEqual(capture.status, Capture.Status.PENDING)

    def test_accepts_one_and_ten_commits(self):
        for count in [1, 10]:
            with self.subTest(count=count):
                job = create_job(
                    self.snapshot,
                    "index.html",
                    self.shas[:count],
                )

                saved_job = Job.objects.get(pk=job.pk)
                self.assertEqual(len(saved_job.captures), count)

    def test_invalid_selections_do_not_create_jobs(self):
        cases = [
            ("missing page", "missing.html", [self.shas[0]]),
            ("no commits", "index.html", []),
            ("too many commits", "index.html", self.shas),
            ("duplicate commits", "index.html", [self.shas[0]] * 2),
            ("unknown commit", "index.html", ["f" * 40]),
        ]

        for label, page_path, commit_shas in cases:
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    create_job(self.snapshot, page_path, commit_shas)

                self.assertEqual(Job.objects.count(), 0)

##########
# Tests for the claim_next_job function (Still Inside Job Tests to reuse setup)

    def test_claim_returns_none_when_queue_is_empty(self):
        self.assertIsNone(claim_next_job())

    def test_claim_marks_job_as_processing(self):
        job = create_job(
            self.snapshot,
            "index.html",
            [self.shas[0]],
        )

        claimed = claim_next_job()

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.pk, job.pk)
        self.assertEqual(claimed.status, Job.Status.PROCESSING)
        self.assertIsNotNone(claimed.started_at)

        # Verify the change was saved.
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PROCESSING)
        self.assertEqual(job.started_at, claimed.started_at)

        # Claiming the job hasn't started individual captures yet.
        self.assertEqual(
            job.captures[0].status,
            Capture.Status.PENDING,
        )

        # The claimed job is no longer available.
        self.assertIsNone(claim_next_job())

    def test_claim_chooses_oldest_queued_job(self):
        newer = create_job(
            self.snapshot,
            "index.html",
            [self.shas[0]],
        )

        older = create_job(
            self.snapshot,
            "about.html",
            [self.shas[1]],
        )

        # Make the second-created record older deliberately.
        Job.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=1),
        )

        self.assertEqual(claim_next_job().pk, older.pk)
        self.assertEqual(claim_next_job().pk, newer.pk)
        self.assertIsNone(claim_next_job())

    def test_claim_ignores_nonqueued_jobs(self):
        statuses = [
            Job.Status.PROCESSING,
            Job.Status.COMPLETE,
            Job.Status.PARTIALLY_COMPLETE,
            Job.Status.FAILED,
        ]

        for status in statuses:
            job = create_job(
                self.snapshot,
                "index.html",
                [self.shas[0]],
            )

            Job.objects.filter(pk=job.pk).update(status=status)

        self.assertIsNone(claim_next_job())
########
# Tests for processing
    def test_processing_records_capture_outcomes(self):
        cases = [
            (
                "all succeed",
                ["first.png", "second.png"],
                Job.Status.COMPLETE,
                [Capture.Status.COMPLETE, Capture.Status.COMPLETE],
            ),
            (
                "first fails but second succeeds",
                [RuntimeError("Page missing"), "second.png"],
                Job.Status.PARTIALLY_COMPLETE,
                [Capture.Status.FAILED, Capture.Status.COMPLETE],
            ),
            (
                "all fail",
                [RuntimeError("Page missing"), RuntimeError("Timeout")],
                Job.Status.FAILED,
                [Capture.Status.FAILED, Capture.Status.FAILED],
            ),
        ]

        for label, outcomes, expected_job_status, expected_capture_statuses in cases:
            with self.subTest(case=label):
                created_job = create_job(
                    self.snapshot,
                    "index.html",
                    self.shas[:2],
                )
                claimed_job = claim_next_job()

                fake_capture = Mock(side_effect=outcomes)

                process_job(claimed_job, fake_capture)

                saved_job = Job.objects.get(pk=created_job.pk)

                self.assertEqual(saved_job.status, expected_job_status)
                self.assertIsNotNone(saved_job.completed_at)
                self.assertEqual(fake_capture.call_count, 2)

                self.assertEqual(
                    [capture.status for capture in saved_job.captures],
                    expected_capture_statuses,
                )

                for capture, outcome in zip(saved_job.captures, outcomes):
                    self.assertIsNotNone(capture.completed_at)

                    if isinstance(outcome, Exception):
                        self.assertEqual(capture.error_message, str(outcome))
                        self.assertEqual(capture.screenshot_path, "")
                    else:
                        self.assertEqual(capture.screenshot_path, outcome)
                        self.assertEqual(capture.error_message, "")
