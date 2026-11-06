import json
from unittest import TestCase
from unittest.mock import patch

import requests

from .services.github import check_repository_html_pages


class RepositoryHtmlPagesTests(TestCase):
    def setUp(self):
        self.repo_url = "https://github.com/example/site"
        self.repository_data = {
            "name": "site",
            "full_name": "example/site",
            "description": "A static website",
            "default_branch": "main",
            "html_url": self.repo_url,
        }
        self.tree_sha = "a" * 40
        self.commit_data = {"commit": {"tree": {"sha": self.tree_sha}}}
        self.tree_data = {
            "sha": self.tree_sha,
            "truncated": False,
            "tree": [
                {"path": "index.html", "type": "blob", "mode": "100644"},
                {"path": "pages", "type": "tree", "mode": "040000"},
                {"path": "pages/about.html", "type": "blob", "mode": "100644"},
            ],
        }
        request_patch = patch("git_gallery_app.services.github.requests.get")
        self.mock_get = request_patch.start()
        self.addCleanup(request_patch.stop)
        self.mock_get.side_effect = AssertionError("Unexpected GitHub request.")

    def make_response(self, data, status_code=200):
        """Build an HTTP response without making a network request."""
        response = requests.Response()
        response.status_code = status_code
        response.url = "https://api.github.com/repos/example/site"
        response._content = json.dumps(data).encode("utf-8")
        return response

    def check_html_pages(self, responses=None):
        self.mock_get.reset_mock()
        if responses is None:
            responses = [
                self.make_response(self.repository_data),
                self.make_response(self.commit_data),
                self.make_response(self.tree_data),
            ]
        self.mock_get.side_effect = responses
        return check_repository_html_pages(self.repo_url)

    def test_finds_root_and_nested_html_pages(self):
        result = self.check_html_pages()

        self.assertEqual(result["html_status"], "passed")
        self.assertEqual(result["html_pages"], ["index.html", "pages/about.html"])
        self.assertEqual(self.mock_get.call_count, 3)

    def test_accepts_case_insensitive_root_index_html(self):
        for homepage in ("index.html", "index.HTML", "INDEX.HTML", "InDeX.HtMl"):
            with self.subTest(homepage=homepage):
                self.tree_data["tree"] = [
                    {"path": homepage, "type": "blob", "mode": "100644"},
                ]

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "passed")
                self.assertEqual(result["html_pages"], [homepage])

    def test_includes_html_and_htm_files_with_mixed_case_extensions(self):
        paths = (
            "about.html", "about.htm", "about.HTML", "about.HTM",
            "pages/About.HtMl", "pages/About.HtM",
        )
        for path in paths:
            with self.subTest(path=path):
                self.tree_data["tree"] = [
                    {"path": "index.html", "type": "blob", "mode": "100644"},
                    {"path": path, "type": "blob", "mode": "100644"},
                ]

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "passed")
                self.assertIn("index.html", result["html_pages"])
                self.assertIn(path, result["html_pages"])
                self.assertEqual(len(result["html_pages"]), 2)

    def test_sorts_paths_without_changing_their_spelling(self):
        self.tree_data["tree"] = [
            {"path": "z.HTML", "type": "blob", "mode": "100644"},
            {"path": "Pages/About Us.HtM", "type": "blob", "mode": "100644"},
            {"path": "a.html", "type": "blob", "mode": "100644"},
            {"path": "INDEX.HTML", "type": "blob", "mode": "100644"},
        ]

        result = self.check_html_pages()

        self.assertEqual(
            result["html_pages"], ["INDEX.HTML", "Pages/About Us.HtM", "a.html", "z.HTML"]
        )

    def test_rejects_missing_root_homepage_even_with_nested_html(self):
        self.tree_data["tree"] = [
            {"path": "docs/index.html", "type": "blob", "mode": "100644"},
            {"path": "vendor/demo.html", "type": "blob", "mode": "100644"},
        ]

        result = self.check_html_pages()

        self.assertEqual(result["html_status"], "rejected")
        self.assertEqual(result["html_pages"], ["docs/index.html", "vendor/demo.html"])
        self.assertIn("root index.html", result["reason"])

    def test_other_index_names_do_not_replace_root_index_html(self):
        for path in ("index.htm", "INDEX.HTM", "my-index.html", "pages/INDEX.HTML"):
            with self.subTest(path=path):
                self.tree_data["tree"] = [
                    {"path": path, "type": "blob", "mode": "100644"},
                ]

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "rejected")
                self.assertEqual(result["html_pages"], [path])
                self.assertIn("root index.html", result["reason"])

    def test_includes_nested_pages_without_directory_exclusions(self):
        self.tree_data["tree"] = [
            {"path": "index.html", "type": "blob", "mode": "100644"},
            {"path": "docs/example.html", "type": "blob", "mode": "100644"},
            {"path": "vendor/demo.html", "type": "blob", "mode": "100644"},
        ]

        result = self.check_html_pages()

        self.assertEqual(result["html_status"], "passed")
        self.assertEqual(
            result["html_pages"], ["docs/example.html", "index.html", "vendor/demo.html"]
        )

    def test_includes_executable_regular_html_files(self):
        self.tree_data["tree"] = [
            {"path": "INDEX.HTML", "type": "blob", "mode": "100755"},
            {"path": "page.htm", "type": "blob", "mode": "100755"},
        ]

        result = self.check_html_pages()

        self.assertEqual(result["html_status"], "passed")
        self.assertEqual(result["html_pages"], ["INDEX.HTML", "page.htm"])

    def test_complete_listing_without_html_is_rejected(self):
        for entries in ([], [{"path": "README.md", "type": "blob", "mode": "100644"}]):
            with self.subTest(entries=entries):
                self.tree_data["tree"] = entries

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "rejected")
                self.assertEqual(result["html_pages"], [])
                self.assertIn("root index.html", result["reason"])

    def test_excludes_directories_symlinks_and_submodules(self):
        self.tree_data["tree"] = [
            {"path": "index.html", "type": "blob", "mode": "100644"},
            {"path": "directory.HTML", "type": "tree", "mode": "040000"},
            {"path": "link.HtM", "type": "blob", "mode": "120000"},
            {"path": "module.htm", "type": "commit", "mode": "160000"},
        ]

        result = self.check_html_pages()

        self.assertEqual(result["html_status"], "passed")
        self.assertEqual(result["html_pages"], ["index.html"])

    def test_root_homepage_must_be_a_regular_file(self):
        entries = (("tree", "040000"), ("blob", "120000"), ("commit", "160000"))
        for entry_type, mode in entries:
            with self.subTest(entry_type=entry_type, mode=mode):
                self.tree_data["tree"] = [
                    {"path": "INDEX.HTML", "type": entry_type, "mode": mode},
                    {"path": "about.htm", "type": "blob", "mode": "100644"},
                ]

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "rejected")
                self.assertEqual(result["html_pages"], ["about.htm"])
                self.assertIn("root index.html", result["reason"])

    def test_excludes_unsupported_extensions(self):
        paths = ("d.xhtml", "e.html.bak", "f.js", "g.htm.bak")
        self.tree_data["tree"] = [
            {"path": "index.html", "type": "blob", "mode": "100644"},
        ]
        for path in paths:
            self.tree_data["tree"].append({"path": path, "type": "blob", "mode": "100644"})

        result = self.check_html_pages()

        self.assertEqual(result["html_status"], "passed")
        self.assertEqual(result["html_pages"], ["index.html"])

    def test_passed_result_does_not_claim_full_compatibility(self):
        result = self.check_html_pages()

        self.assertEqual(set(result), {"html_status", "html_pages", "reason"})
        self.assertIn("dependency checks are still required", result["reason"])
        self.assertIn("Page rendering", result["reason"])

    def test_uses_encoded_default_branch_then_fixed_recursive_tree(self):
        self.repository_data["default_branch"] = "release/site"

        self.check_html_pages()

        metadata_request, commit_request, tree_request = self.mock_get.call_args_list
        self.assertEqual(metadata_request.args, ("https://api.github.com/repos/example/site",))
        self.assertEqual(
            commit_request.args,
            ("https://api.github.com/repos/example/site/commits/heads%2Frelease%2Fsite",),
        )
        self.assertEqual(
            tree_request.args,
            (f"https://api.github.com/repos/example/site/git/trees/{self.tree_sha}",),
        )
        self.assertEqual(tree_request.kwargs["params"], {"recursive": "1"})
        self.assertEqual(commit_request.kwargs["timeout"], 10)
        self.assertEqual(tree_request.kwargs["timeout"], 10)

    def test_missing_default_branch_is_rejected_before_commit_lookup(self):
        for default_branch in (None, "", "   "):
            with self.subTest(default_branch=default_branch):
                self.repository_data["default_branch"] = default_branch

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "rejected")
                self.assertEqual(result["html_pages"], [])
                self.assertIn("no usable default branch", result["reason"])
                self.assertEqual(self.mock_get.call_count, 1)

    def test_truncated_listing_is_unavailable_even_with_candidates(self):
        for entries in ([], self.tree_data["tree"]):
            with self.subTest(entries=entries):
                self.tree_data["truncated"] = True
                self.tree_data["tree"] = entries

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "unavailable")
                self.assertEqual(result["html_pages"], [])
                self.assertIn("incomplete file listing", result["reason"])

    def test_malformed_tree_responses_are_unavailable(self):
        payloads = (
            None,
            [],
            {},
            {"sha": self.tree_sha, "tree": []},
            {"sha": self.tree_sha, "tree": [], "truncated": "false"},
            {"sha": self.tree_sha, "tree": [], "truncated": 0},
            {"sha": self.tree_sha, "tree": {}, "truncated": False},
            {"sha": "b" * 40, "tree": [], "truncated": False},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                self.tree_data = payload

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "unavailable")
                self.assertEqual(result["html_pages"], [])

    def test_malformed_entries_do_not_allow_partial_results(self):
        invalid_entries = (
            None,
            {},
            {"path": "bad.html", "type": "blob"},
            {"path": 123, "type": "blob", "mode": "100644"},
            {"path": "", "type": "blob", "mode": "100644"},
            {"path": "/absolute.html", "type": "blob", "mode": "100644"},
            {"path": "../outside.html", "type": "blob", "mode": "100644"},
            {"path": "a//b.html", "type": "blob", "mode": "100644"},
            {"path": "bad.html", "type": "tree", "mode": "100644"},
            {"path": "bad.html", "type": "blob", "mode": "unknown"},
            {"path": "bad.html", "type": "blob", "mode": []},
        )
        for entry in invalid_entries:
            with self.subTest(entry=entry):
                self.tree_data["tree"] = [
                    {"path": "INDEX.HTML", "type": "blob", "mode": "100644"},
                    entry,
                ]

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "unavailable")
                self.assertEqual(result["html_pages"], [])

    def test_malformed_commit_responses_are_unavailable(self):
        payloads = (None, [], {}, {"commit": {}}, {"commit": {"tree": None}})
        for payload in payloads:
            with self.subTest(payload=payload):
                self.commit_data = payload

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "unavailable")
                self.assertEqual(self.mock_get.call_count, 2)

    def test_invalid_tree_identifier_is_unavailable(self):
        for tree_sha in (None, "", "main", "z" * 40, 123, []):
            with self.subTest(tree_sha=tree_sha):
                self.commit_data = {"commit": {"tree": {"sha": tree_sha}}}

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "unavailable")
                self.assertEqual(self.mock_get.call_count, 2)

    def test_malformed_metadata_is_unavailable(self):
        for payload in (None, [], {}, {**self.repository_data, "default_branch": 123}):
            with self.subTest(payload=payload):
                self.repository_data = payload

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "unavailable")
                self.assertEqual(self.mock_get.call_count, 1)

    def test_invalid_json_at_each_request_is_unavailable(self):
        for request_number in range(3):
            with self.subTest(request_number=request_number):
                responses = [
                    self.make_response(self.repository_data),
                    self.make_response(self.commit_data),
                    self.make_response(self.tree_data),
                ]
                responses[request_number]._content = b"not JSON"

                result = self.check_html_pages(responses)

                self.assertEqual(result["html_status"], "unavailable")
                self.assertEqual(result["html_pages"], [])

    def test_http_failures_at_each_request_are_unavailable(self):
        for request_number in range(3):
            for status_code in (401, 403, 404, 409, 422, 429, 500, 503):
                with self.subTest(request_number=request_number, status_code=status_code):
                    responses = [
                        self.make_response(self.repository_data),
                        self.make_response(self.commit_data),
                        self.make_response(self.tree_data),
                    ]
                    responses[request_number] = self.make_response({}, status_code)

                    result = self.check_html_pages(responses)

                    self.assertEqual(result["html_status"], "unavailable")
                    self.assertEqual(result["html_pages"], [])
                    self.assertIn("Try again", result["reason"])

    def test_timeouts_and_connection_failures_are_unavailable(self):
        for request_number in range(3):
            for error in (requests.Timeout(), requests.ConnectionError()):
                with self.subTest(request_number=request_number, error=type(error).__name__):
                    responses = [
                        self.make_response(self.repository_data),
                        self.make_response(self.commit_data),
                        self.make_response(self.tree_data),
                    ]
                    responses[request_number] = error

                    result = self.check_html_pages(responses)

                    self.assertEqual(result["html_status"], "unavailable")
                    self.assertEqual(result["html_pages"], [])

    def test_invalid_url_is_rejected_without_network_calls(self):
        for repo_url in (None, "", "https://example.com/owner/repo"):
            with self.subTest(repo_url=repo_url):
                self.repo_url = repo_url

                result = self.check_html_pages()

                self.assertEqual(result["html_status"], "rejected")
                self.assertEqual(result["html_pages"], [])
                self.assertTrue(result["reason"])
                self.mock_get.assert_not_called()
