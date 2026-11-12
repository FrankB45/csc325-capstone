from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from ..services.github import get_repository_compatibility_report


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
        self.dependency_result = {
            "dependency_status": "pending",
            "reason": "This limited check has not established an unsupported dependency.",
            "evidence_paths": ["index.html", "src/main.js"],
            "tree_sha": "a" * 40,
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

        dependency_patch = patch(
            "git_gallery_app.services.dependencies.check_repository_dependencies",
            return_value=self.dependency_result,
        )
        self.mock_dependency_check = dependency_patch.start()
        self.addCleanup(dependency_patch.stop)

        request_patch = patch(
            "git_gallery_app.services.github.requests.get",
            side_effect=AssertionError("The coordinator must not make network requests."),
        )
        request_patch.start()
        self.addCleanup(request_patch.stop)

    def test_all_status_combinations(self):
        cases = (
            ("passed", "passed", "pending", "pending"),
            ("passed", "rejected", "pending", "rejected"),
            ("passed", "unavailable", "pending", "unavailable"),
            ("rejected", "passed", "pending", "rejected"),
            ("rejected", "rejected", "pending", "rejected"),
            ("rejected", "unavailable", "pending", "rejected"),
            ("unavailable", "passed", "pending", "unavailable"),
            ("unavailable", "rejected", "pending", "rejected"),
            ("unavailable", "unavailable", "pending", "unavailable"),
            ("passed", "passed", "rejected", "rejected"),
            ("passed", "rejected", "rejected", "rejected"),
            ("passed", "unavailable", "rejected", "rejected"),
            ("rejected", "passed", "rejected", "rejected"),
            ("rejected", "rejected", "rejected", "rejected"),
            ("rejected", "unavailable", "rejected", "rejected"),
            ("unavailable", "passed", "rejected", "rejected"),
            ("unavailable", "rejected", "rejected", "rejected"),
            ("unavailable", "unavailable", "rejected", "rejected"),
            ("passed", "passed", "unavailable", "unavailable"),
            ("passed", "rejected", "unavailable", "rejected"),
            ("passed", "unavailable", "unavailable", "unavailable"),
            ("rejected", "passed", "unavailable", "rejected"),
            ("rejected", "rejected", "unavailable", "rejected"),
            ("rejected", "unavailable", "unavailable", "rejected"),
            ("unavailable", "passed", "unavailable", "unavailable"),
            ("unavailable", "rejected", "unavailable", "rejected"),
            ("unavailable", "unavailable", "unavailable", "unavailable"),
            ("passed", "passed", "passed", "accepted"),
            ("passed", "rejected", "passed", "rejected"),
            ("passed", "unavailable", "passed", "unavailable"),
            ("rejected", "passed", "passed", "rejected"),
            ("rejected", "rejected", "passed", "rejected"),
            ("rejected", "unavailable", "passed", "rejected"),
            ("unavailable", "passed", "passed", "unavailable"),
            ("unavailable", "rejected", "passed", "rejected"),
            ("unavailable", "unavailable", "passed", "unavailable"),
            ("pending", "passed", "passed", "pending"),
            ("passed", "pending", "passed", "pending"),
            ("pending", "pending", "pending", "pending"),
            ("pending", "unavailable", "passed", "unavailable"),
            ("passed", "pending", "unavailable", "unavailable"),
            ("rejected", "pending", "passed", "rejected"),
            ("pending", "rejected", "passed", "rejected"),
            ("pending", "passed", "unknown", "unavailable"),
        )
        for history_status, html_status, dependency_status, expected_status in cases:
            with self.subTest(
                history_status=history_status,
                html_status=html_status,
                dependency_status=dependency_status,
            ):
                self.history_result["history_status"] = history_status
                self.html_result["html_status"] = html_status
                self.dependency_result["dependency_status"] = dependency_status
                self.mock_history_check.reset_mock()
                self.mock_html_check.reset_mock()
                self.mock_dependency_check.reset_mock()

                report = get_repository_compatibility_report(self.repo_url)

                self.assertEqual(report["overall_status"], expected_status)
                self.assertTrue(report["reason"])
                if expected_status == "accepted":
                    self.assertIs(report["setup_available"], True)
                else:
                    self.assertIs(report["setup_available"], False)
                self.assertIs(report["same_snapshot_guaranteed"], False)
                self.mock_history_check.assert_called_once_with(self.repo_url)
                self.mock_html_check.assert_called_once_with(self.repo_url)
                self.mock_dependency_check.assert_called_once_with(self.repo_url)

    def test_preserves_individual_results_and_available_data(self):
        original_history = deepcopy(self.history_result)
        original_html = deepcopy(self.html_result)
        original_dependencies = deepcopy(self.dependency_result)

        report = get_repository_compatibility_report(self.repo_url)

        self.assertEqual(report["history"], original_history)
        self.assertEqual(report["html"], original_html)
        self.assertEqual(report["history"]["commit_count"], 12)
        self.assertEqual(report["html"]["html_pages"], ["index.html", "pages/about.html"])
        self.assertEqual(report["dependencies"], {
            "status": "pending",
            "reason": original_dependencies["reason"],
            "evidence_paths": original_dependencies["evidence_paths"],
            "tree_sha": original_dependencies["tree_sha"],
        })
        self.assertEqual(self.history_result, original_history)
        self.assertEqual(self.html_result, original_html)
        self.assertEqual(self.dependency_result, original_dependencies)
        self.assertNotIn("dependency_status", report["dependencies"])

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

    def test_calls_each_check_once_even_when_history_rejects(self):
        self.mock_history_check.return_value = {
            "history_status": "rejected",
            "reason": "The default-branch history exceeds the 50-commit limit.",
        }

        report = get_repository_compatibility_report(self.repo_url)

        self.mock_history_check.assert_called_once_with(self.repo_url)
        self.mock_html_check.assert_called_once_with(self.repo_url)
        self.mock_dependency_check.assert_called_once_with(self.repo_url)
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
                self.assertEqual(
                    report["dependencies"]["reason"], self.dependency_result["reason"]
                )
                self.assertIs(report["setup_available"], False)

    def test_dependency_rejection_preserves_package_explanation_and_evidence(self):
        self.dependency_result["dependency_status"] = "rejected"
        self.dependency_result["reason"] = (
            "Homepage 'index.html' requires startup file 'src/main.js', which imports "
            "package 'react-dom/client' without a browser import map."
        )
        original_dependencies = deepcopy(self.dependency_result)

        report = get_repository_compatibility_report(self.repo_url)

        self.assertEqual(report["overall_status"], "rejected")
        self.assertEqual(report["dependencies"]["status"], "rejected")
        self.assertEqual(report["dependencies"]["reason"], original_dependencies["reason"])
        self.assertEqual(report["dependencies"]["evidence_paths"], ["index.html", "src/main.js"])
        self.assertEqual(report["dependencies"]["tree_sha"], original_dependencies["tree_sha"])
        self.assertEqual(self.dependency_result, original_dependencies)

    def test_dependency_unavailable_preserves_failure_details(self):
        self.dependency_result["dependency_status"] = "unavailable"
        self.dependency_result["reason"] = "Could not retrieve the fixed repository snapshot from GitHub."

        report = get_repository_compatibility_report(self.repo_url)

        self.assertEqual(report["overall_status"], "unavailable")
        self.assertEqual(report["dependencies"]["status"], "unavailable")
        self.assertEqual(report["dependencies"]["reason"], self.dependency_result["reason"])
        self.assertEqual(report["dependencies"]["evidence_paths"], self.dependency_result["evidence_paths"])
        self.assertEqual(report["dependencies"]["tree_sha"], self.dependency_result["tree_sha"])

    def test_missing_or_unknown_status_is_unavailable(self):
        # Otherwise every check passes, so each invalid status must block setup itself.
        self.dependency_result["dependency_status"] = "passed"
        cases = (
            ({"reason": "Missing history status."}, self.html_result, self.dependency_result),
            ({"history_status": None}, self.html_result, self.dependency_result),
            ({"history_status": "unknown"}, self.html_result, self.dependency_result),
            (self.history_result, {"reason": "Missing HTML status."}, self.dependency_result),
            (self.history_result, {"html_status": None}, self.dependency_result),
            (self.history_result, {"html_status": "unknown"}, self.dependency_result),
            (self.history_result, self.html_result, {"reason": "Missing dependency status."}),
            (self.history_result, self.html_result, {"dependency_status": None}),
            (self.history_result, self.html_result, {"dependency_status": "unknown"}),
            (self.history_result, self.html_result, {"dependency_status": "compatible"}),
            (self.history_result, self.html_result, {"dependency_status": []}),
        )
        for history_result, html_result, dependency_result in cases:
            with self.subTest(
                history_result=history_result,
                html_result=html_result,
                dependency_result=dependency_result,
            ):
                self.mock_history_check.return_value = history_result
                self.mock_html_check.return_value = html_result
                self.mock_dependency_check.return_value = dependency_result

                report = get_repository_compatibility_report(self.repo_url)

                self.assertEqual(report["overall_status"], "unavailable")
                self.assertIs(report["setup_available"], False)
                self.assertIs(report["same_snapshot_guaranteed"], False)

    def test_known_rejection_takes_precedence_over_unknown_statuses(self):
        cases = (
            ({"history_status": "rejected"}, self.html_result, {}),
            (self.history_result, {"html_status": "rejected"}, {"dependency_status": "unknown"}),
            ({}, self.html_result, {"dependency_status": "rejected"}),
        )
        for history_result, html_result, dependency_result in cases:
            with self.subTest(
                history_result=history_result,
                html_result=html_result,
                dependency_result=dependency_result,
            ):
                self.mock_history_check.return_value = history_result
                self.mock_html_check.return_value = html_result
                self.mock_dependency_check.return_value = dependency_result

                report = get_repository_compatibility_report(self.repo_url)

                self.assertEqual(report["overall_status"], "rejected")
                self.assertIs(report["setup_available"], False)

    def test_report_does_not_claim_a_shared_snapshot(self):
        report = get_repository_compatibility_report(self.repo_url)

        self.assertIs(report["same_snapshot_guaranteed"], False)

    def test_explicit_passes_make_setup_available_under_the_limited_profile(self):
        self.dependency_result["dependency_status"] = "passed"
        self.dependency_result["reason"] = "The homepage conforms to the bounded passive profile."
        self.dependency_result["evidence_paths"] = ["INDEX.HTML", "css/site.css", "images/logo.png"]
        original_history = deepcopy(self.history_result)
        original_html = deepcopy(self.html_result)
        original_dependencies = deepcopy(self.dependency_result)

        report = get_repository_compatibility_report(self.repo_url)

        self.assertEqual(report["overall_status"], "accepted")
        self.assertIn("limited supported-site profile for entering project setup", report["reason"])
        self.assertIn("does not guarantee screenshot success or complete dependency detection", report["reason"])
        self.assertIn("Multiple-independent-website detection is deferred", report["reason"])
        self.assertEqual(report["history"], original_history)
        self.assertEqual(report["html"], original_html)
        self.assertEqual(self.history_result, original_history)
        self.assertEqual(self.html_result, original_html)
        self.assertEqual(report["dependencies"]["status"], "passed")
        self.assertEqual(report["dependencies"]["reason"], original_dependencies["reason"])
        self.assertEqual(report["dependencies"]["evidence_paths"], original_dependencies["evidence_paths"])
        self.assertEqual(report["dependencies"]["tree_sha"], original_dependencies["tree_sha"])
        self.assertEqual(self.dependency_result, original_dependencies)
        self.assertIs(report["setup_available"], True)
        self.assertIs(report["same_snapshot_guaranteed"], False)
        self.mock_history_check.assert_called_once_with(self.repo_url)
        self.mock_html_check.assert_called_once_with(self.repo_url)
        self.mock_dependency_check.assert_called_once_with(self.repo_url)
