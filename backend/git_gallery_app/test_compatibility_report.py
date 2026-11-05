from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from .services.github import get_repository_compatibility_report


class RepositoryCompatibilityReportTests(TestCase):
    def setUp(self):
        self.repo_url = "https://github.com/example/site"
        self.history_result = {
            "history_status": "passed",
            "reason": "History meets the commit limit.",
            "commit_count": 12,
        }
        self.html_result = {
            "html_status": "passed",
            "reason": "Candidate HTML filenames were found.",
            "html_pages": ["index.html", "pages/about.html"],
        }

        history_patch = patch(
            "git_gallery_app.services.github.check_repository_history",
            return_value=self.history_result,
        )
        self.mock_history_check = history_patch.start()
        self.addCleanup(history_patch.stop)

        html_patch = patch(
            "git_gallery_app.services.github.check_repository_html_pages",
            return_value=self.html_result,
        )
        self.mock_html_check = html_patch.start()
        self.addCleanup(html_patch.stop)

        request_patch = patch(
            "git_gallery_app.services.github.requests.get",
            side_effect=AssertionError("The coordinator must not make network requests."),
        )
        request_patch.start()
        self.addCleanup(request_patch.stop)

    def test_all_status_combinations(self):
        cases = (
            ("passed", "passed", "pending"),
            ("passed", "rejected", "rejected"),
            ("passed", "unavailable", "unavailable"),
            ("rejected", "passed", "rejected"),
            ("rejected", "rejected", "rejected"),
            ("rejected", "unavailable", "rejected"),
            ("unavailable", "passed", "unavailable"),
            ("unavailable", "rejected", "rejected"),
            ("unavailable", "unavailable", "unavailable"),
        )
        for history_status, html_status, expected_status in cases:
            with self.subTest(history_status=history_status, html_status=html_status):
                self.history_result["history_status"] = history_status
                self.html_result["html_status"] = html_status

                report = get_repository_compatibility_report(self.repo_url)

                self.assertEqual(report["overall_status"], expected_status)
                self.assertTrue(report["reason"])

    def test_preserves_individual_results_and_available_data(self):
        original_history = deepcopy(self.history_result)
        original_html = deepcopy(self.html_result)

        report = get_repository_compatibility_report(self.repo_url)

        self.assertEqual(report["history"], original_history)
        self.assertEqual(report["html"], original_html)
        self.assertEqual(report["history"]["commit_count"], 12)
        self.assertEqual(report["html"]["html_pages"], ["index.html", "pages/about.html"])
        self.assertEqual(self.history_result, original_history)
        self.assertEqual(self.html_result, original_html)

    def test_preserves_failure_reason_without_inventing_commit_count(self):
        self.mock_history_check.return_value = {
            "history_status": "unavailable",
            "reason": "GitHub is limiting requests. Try again later.",
        }

        report = get_repository_compatibility_report(self.repo_url)

        self.assertEqual(report["overall_status"], "unavailable")
        self.assertEqual(report["history"], self.mock_history_check.return_value)
        self.assertNotIn("commit_count", report["history"])
        self.assertEqual(report["html"], self.html_result)

    def test_calls_both_checks_once_even_when_history_rejects(self):
        self.mock_history_check.return_value = {
            "history_status": "rejected",
            "reason": "The default-branch history exceeds the 50-commit limit.",
        }

        report = get_repository_compatibility_report(self.repo_url)

        self.mock_history_check.assert_called_once_with(self.repo_url)
        self.mock_html_check.assert_called_once_with(self.repo_url)
        self.assertEqual(report["overall_status"], "rejected")
        self.assertEqual(report["history"], self.mock_history_check.return_value)
        self.assertEqual(report["html"], self.html_result)

    def test_dependencies_remain_pending_and_setup_stays_unavailable(self):
        cases = (
            ("passed", "passed"),
            ("rejected", "passed"),
            ("unavailable", "passed"),
        )
        for history_status, html_status in cases:
            with self.subTest(history_status=history_status, html_status=html_status):
                self.history_result["history_status"] = history_status
                self.html_result["html_status"] = html_status

                report = get_repository_compatibility_report(self.repo_url)

                self.assertEqual(report["dependencies"]["status"], "pending")
                self.assertIn("not implemented", report["dependencies"]["reason"])
                self.assertIs(report["setup_available"], False)

    def test_missing_or_unknown_status_is_unavailable(self):
        cases = (
            ({"reason": "Missing history status."}, self.html_result),
            ({"history_status": None}, self.html_result),
            ({"history_status": "unknown"}, self.html_result),
            (self.history_result, {"reason": "Missing HTML status."}),
            (self.history_result, {"html_status": None}),
            (self.history_result, {"html_status": "unknown"}),
        )
        for history_result, html_result in cases:
            with self.subTest(history_result=history_result, html_result=html_result):
                self.mock_history_check.return_value = history_result
                self.mock_html_check.return_value = html_result

                report = get_repository_compatibility_report(self.repo_url)

                self.assertEqual(report["overall_status"], "unavailable")

    def test_report_does_not_claim_a_shared_snapshot(self):
        report = get_repository_compatibility_report(self.repo_url)

        self.assertIs(report["same_snapshot_guaranteed"], False)
