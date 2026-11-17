from copy import deepcopy
from unittest.mock import patch

import requests
from django.urls import reverse
from rest_framework.test import APISimpleTestCase


class RepositoryCompatibilityApiTests(APISimpleTestCase):
    def setUp(self):
        self.endpoint = reverse("check-repository-compatibility")
        self.repo_url = "https://github.com/example/site"
        self.report = {
            "overall_status": "pending",
            "reason": "History and candidate HTML checks passed; dependency checking is unfinished.",
            "history": {
                "history_status": "passed",
                "reason": "History meets the commit limit.",
                "commit_count": 12,
            },
            "html": {
                "html_status": "passed",
                "reason": "Candidate HTML filenames were found.",
                "html_pages": ["index.html", "pages/about.html"],
            },
            "dependencies": {
                "status": "pending",
                "reason": "This limited check has not established an unsupported dependency.",
                "evidence_paths": ["index.html", "src/main.js"],
                "tree_sha": "a" * 40,
            },
            "setup_available": False,
            "same_snapshot_guaranteed": False,
        }
        report_patch = patch(
            "git_gallery_app.views.get_repository_compatibility_report",
            return_value=self.report,
        )
        self.mock_report = report_patch.start()
        self.addCleanup(report_patch.stop)

        self.repository = {
            "name": "site",
            "full_name": "example/site",
            "description": "A static website",
            "default_branch": "main",
            "url": self.repo_url,
        }
        information_patch = patch(
            "git_gallery_app.views.get_repository_information",
            return_value=self.repository,
        )
        self.mock_information = information_patch.start()
        self.addCleanup(information_patch.stop)

        request_patch = patch(
            "git_gallery_app.services.github.requests.get",
            side_effect=AssertionError("API tests must not make GitHub requests."),
        )
        request_patch.start()
        self.addCleanup(request_patch.stop)

    def test_post_calls_report_service_with_url(self):
        response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(self.endpoint, "/api/repo/compatibility/")
        self.assertEqual(response.status_code, 200)
        self.mock_report.assert_called_once_with(self.repo_url)
        self.mock_information.assert_not_called()

    def test_post_trims_surrounding_url_whitespace(self):
        response = self.client.post(
            self.endpoint, {"url": f"  {self.repo_url}\n"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.mock_report.assert_called_once_with(self.repo_url)

    def test_pending_report_is_preserved_without_enabling_setup(self):
        original_report = deepcopy(self.report)

        response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), original_report)
        self.assertEqual(self.report, original_report)
        self.assertIs(response.json()["setup_available"], False)
        self.assertIs(response.json()["same_snapshot_guaranteed"], False)

    def test_rejected_report_preserves_specific_reason(self):
        self.report["overall_status"] = "rejected"
        self.report["reason"] = "An implemented check found a failed repository prerequisite."
        self.report["history"] = {
            "history_status": "rejected",
            "reason": "The default-branch history exceeds the 50-commit limit.",
        }

        response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.report)
        self.assertEqual(
            response.json()["history"]["reason"],
            "The default-branch history exceeds the 50-commit limit.",
        )

    def test_rejection_is_returned_even_when_another_check_is_unavailable(self):
        self.report["overall_status"] = "rejected"
        self.report["history"] = {
            "history_status": "rejected",
            "reason": "The default branch has no commits.",
        }
        self.report["html"] = {
            "html_status": "unavailable",
            "html_pages": [],
            "reason": "GitHub could not complete HTML-page discovery.",
        }

        response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.report)

    def test_unavailable_report_returns_502_with_individual_results(self):
        self.report["overall_status"] = "unavailable"
        self.report["reason"] = "At least one implemented check could not complete reliably."
        self.report["html"] = {
            "html_status": "unavailable",
            "html_pages": [],
            "reason": "GitHub returned an incomplete file listing. Try again.",
        }

        response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), self.report)
        self.assertEqual(response.json()["history"]["commit_count"], 12)

    def test_dependency_rejection_returns_200_with_explanation_and_evidence(self):
        self.report["overall_status"] = "rejected"
        self.report["reason"] = "An implemented check found a failed repository prerequisite."
        self.report["dependencies"]["status"] = "rejected"
        self.report["dependencies"]["reason"] = (
            "Homepage 'index.html' requires startup file 'src/main.js', which imports "
            "package 'react-dom/client' without a browser import map."
        )
        original_report = deepcopy(self.report)

        response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), original_report)
        self.assertEqual(self.report, original_report)
        self.assertEqual(response.json()["dependencies"]["status"], "rejected")
        self.assertEqual(
            response.json()["dependencies"]["reason"], original_report["dependencies"]["reason"]
        )
        self.assertEqual(
            response.json()["dependencies"]["evidence_paths"], ["index.html", "src/main.js"]
        )
        self.assertEqual(response.json()["dependencies"]["tree_sha"], "a" * 40)

    def test_dependency_unavailable_returns_502_with_report_fields(self):
        self.report["overall_status"] = "unavailable"
        self.report["reason"] = "At least one implemented check could not complete reliably."
        self.report["dependencies"]["status"] = "unavailable"
        self.report["dependencies"]["reason"] = "Could not retrieve the fixed repository snapshot from GitHub."
        original_report = deepcopy(self.report)

        response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), original_report)
        self.assertEqual(self.report, original_report)
        self.assertEqual(response.json()["dependencies"]["status"], "unavailable")
        self.assertEqual(
            response.json()["dependencies"]["evidence_paths"], ["index.html", "src/main.js"]
        )
        self.assertEqual(response.json()["dependencies"]["tree_sha"], "a" * 40)

    def test_accepted_report_returns_200_with_setup_available(self):
        self.report["overall_status"] = "accepted"
        self.report["setup_available"] = True
        self.report["dependencies"]["status"] = "passed"
        self.report["dependencies"]["reason"] = (
            "The homepage meets the static-hosting prerequisite policy. JavaScript behavior, "
            "indirect resources, external availability and screenshot success remain unverified."
        )
        self.report["reason"] = (
            "The repository meets the limited supported-site profile for entering project setup. "
            "This does not guarantee screenshot success or complete dependency detection. "
            "Multiple-independent-website detection is deferred from this MVP setup gate."
        )
        original_report = deepcopy(self.report)

        response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), original_report)
        self.assertEqual(self.report, original_report)
        self.assertEqual(response.json()["dependencies"]["status"], "passed")
        self.assertEqual(response.json()["dependencies"]["reason"], original_report["dependencies"]["reason"])
        self.assertIn("remain unverified", response.json()["dependencies"]["reason"])
        self.assertEqual(response.json()["overall_status"], "accepted")
        self.assertIs(response.json()["setup_available"], True)
        self.assertIs(response.json()["same_snapshot_guaranteed"], False)
        self.mock_report.assert_called_once_with(self.repo_url)

    def test_non_object_json_is_rejected_before_calling_service(self):
        for body in ("[]", '"a string"', "null", "123", "true"):
            with self.subTest(body=body):
                response = self.client.post(
                    self.endpoint, body, content_type="application/json"
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json(), {"error": "Send a JSON object containing a url."}
                )
                self.mock_report.assert_not_called()

    def test_missing_url_is_rejected(self):
        response = self.client.post(self.endpoint, {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Include a url in the request."})
        self.mock_report.assert_not_called()

    def test_non_string_urls_are_rejected(self):
        for url in (None, 123, True, [], {}):
            with self.subTest(url=url):
                response = self.client.post(self.endpoint, {"url": url}, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"error": "The url must be a string."})
                self.mock_report.assert_not_called()

    def test_empty_and_whitespace_only_urls_are_rejected(self):
        for url in ("", "   ", "\t\n"):
            with self.subTest(url=url):
                response = self.client.post(self.endpoint, {"url": url}, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"error": "Enter a repository URL."})
                self.mock_report.assert_not_called()

    def test_malformed_json_uses_drf_parse_error_response(self):
        response = self.client.post(
            self.endpoint, '{"url":', content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())
        self.mock_report.assert_not_called()

    def test_unsupported_methods_use_drf_method_not_allowed_response(self):
        for method in ("GET", "PUT", "PATCH", "DELETE", "HEAD"):
            with self.subTest(method=method):
                response = self.client.generic(method, self.endpoint)

                self.assertEqual(response.status_code, 405)
                self.assertIn("POST", response["Allow"])
                self.mock_report.assert_not_called()

    def test_options_remains_available_through_drf(self):
        response = self.client.options(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertIn("POST", response["Allow"])
        self.mock_report.assert_not_called()

    def test_unsupported_content_type_uses_drf_response(self):
        response = self.client.post(self.endpoint, "url=example", content_type="text/plain")

        self.assertEqual(response.status_code, 415)
        self.assertIn("detail", response.json())
        self.mock_report.assert_not_called()

    def test_unexpected_service_exception_is_logged_but_not_returned(self):
        self.mock_report.side_effect = RuntimeError("private diagnostic text")

        with self.assertLogs("git_gallery_app.views", level="ERROR") as captured_logs:
            response = self.client.post(self.endpoint, {"url": self.repo_url}, format="json")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"error": "Could not complete the compatibility check. Try again."},
        )
        self.assertNotIn("private diagnostic text", response.content.decode())
        self.assertIn("private diagnostic text", "\n".join(captured_logs.output))

    def test_invalid_report_status_returns_generic_error(self):
        for report in (None, [], {}, {"overall_status": "compatible"}):
            with self.subTest(report=report):
                self.mock_report.return_value = report

                with self.assertLogs("git_gallery_app.views", level="ERROR"):
                    response = self.client.post(
                        self.endpoint, {"url": self.repo_url}, format="json"
                    )

                self.assertEqual(response.status_code, 500)
                self.assertEqual(
                    response.json(),
                    {"error": "Could not complete the compatibility check. Try again."},
                )

    def test_existing_hello_endpoint_keeps_its_response(self):
        response = self.client.get(reverse("hello-world"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, Git Gallery!"})
        self.mock_report.assert_not_called()
        self.mock_information.assert_not_called()

    def test_existing_hello_endpoint_still_rejects_post(self):
        response = self.client.post(reverse("hello-world"), {}, format="json")

        self.assertEqual(response.status_code, 405)

    def test_existing_repository_info_endpoint_keeps_its_response(self):
        response = self.client.post(
            reverse("get-repository-info"), {"url": self.repo_url}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.repository)
        self.mock_information.assert_called_once_with(self.repo_url)
        self.mock_report.assert_not_called()

    def test_existing_repository_info_endpoint_rejects_non_object_body(self):
        response = self.client.post(reverse("get-repository-info"), [], format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Send a JSON object containing a url."})
        self.mock_information.assert_not_called()

    def test_existing_repository_info_endpoint_keeps_url_error_response(self):
        self.mock_information.side_effect = ValueError("URL parser input must be a string.")

        response = self.client.post(reverse("get-repository-info"), {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "URL parser input must be a string."})

    def test_existing_repository_info_endpoint_keeps_http_error_responses(self):
        cases = (
            (404, 404, "Repository not found or not publicly accessible."),
            (500, 502, "GitHub could not complete the request."),
        )
        for upstream_status, expected_status, message in cases:
            with self.subTest(upstream_status=upstream_status):
                upstream_response = requests.Response()
                upstream_response.status_code = upstream_status
                self.mock_information.side_effect = requests.HTTPError(response=upstream_response)

                response = self.client.post(
                    reverse("get-repository-info"), {"url": self.repo_url}, format="json"
                )

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json(), {"error": message})

    def test_existing_repository_info_endpoint_keeps_network_error_response(self):
        self.mock_information.side_effect = requests.Timeout()

        response = self.client.post(
            reverse("get-repository-info"), {"url": self.repo_url}, format="json"
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json(), {"error": "Could not retrieve data from GitHub. Try again."}
        )

    def test_existing_repository_info_endpoint_still_rejects_get(self):
        response = self.client.get(reverse("get-repository-info"))

        self.assertEqual(response.status_code, 405)
        self.mock_information.assert_not_called()
