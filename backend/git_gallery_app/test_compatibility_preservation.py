import json
from unittest.mock import patch

import requests
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITransactionTestCase

from .models import Capture, Commit, Job, Project, RepositorySnapshot
from .services import analyses
from .services.jobs import create_job


class CompatibilityRecheckPreservationTests(APITransactionTestCase):
    def setUp(self):
        # Block the hardcoded application collection before checking test storage.
        storage_patch = patch.object(analyses, "_collection", object())
        storage_patch.start()
        self.addCleanup(storage_patch.stop)

        self.assertEqual(connection.settings_dict["NAME"], "test_git_gallery")
        self.database = connection.database
        self.assertEqual(self.database.name, "test_git_gallery")

        # Django does not redirect the analysis service's cached PyMongo collection.
        self.analysis_collection = self.database["analyses"]
        analyses._collection = self.analysis_collection
        self.addCleanup(self.analysis_collection.drop)

        request_patch = patch("git_gallery_app.services.github.requests.get")
        self.mock_get = request_patch.start()
        self.addCleanup(request_patch.stop)
        self.mock_get.side_effect = AssertionError("Unexpected GitHub request.")

        self.repo_url = "https://github.com/example/site"
        self.commit_sha = "1" * 40
        self.tree_sha = "a" * 40
        saved_at = timezone.now().replace(microsecond=0)
        saved_snapshot = {
            "url": self.repo_url,
            "page_path": "index.html",
            "commits": [
                {
                    "sha": self.commit_sha,
                    "message": "Original homepage",
                    "date": saved_at.isoformat(),
                },
            ],
            "created_at": saved_at.isoformat(),
        }
        self.saved_analysis = analyses.save_analysis(saved_snapshot)

        # Analysis documents and the project/job models are currently separate.
        project = Project.objects.create(
            name="Earlier saved project",
            repository_url=self.repo_url,
        )
        repository_snapshot = RepositorySnapshot.objects.create(
            project=project,
            repository_url=self.repo_url,
            default_branch="main",
            head_sha=self.commit_sha,
            commits=[
                Commit(
                    sha=self.commit_sha,
                    message="Original homepage",
                    author_name="Test Author",
                    committed_at=saved_at,
                    position=0,
                ),
            ],
            available_pages=["index.html"],
            default_page="index.html",
        )
        job = create_job(repository_snapshot, "index.html", [self.commit_sha])
        job.status = Job.Status.COMPLETE
        job.started_at = saved_at
        job.completed_at = saved_at
        job.captures[0].status = Capture.Status.COMPLETE
        job.captures[0].screenshot_path = "test-captures/original-homepage.png"
        job.captures[0].completed_at = saved_at
        job.save()

        self.saved_documents = {}
        for collection_name in ("analyses", "projects", "repository_snapshots", "jobs"):
            collection = self.database[collection_name]
            self.assertEqual(collection.count_documents({}), 1)
            self.saved_documents[collection_name] = collection.find_one({})
        self.assertEqual(
            self.saved_analysis["id"], str(self.saved_documents["analyses"]["_id"])
        )

        self.repository_data = {
            "name": "site",
            "full_name": "example/site",
            "description": "A static website",
            "default_branch": "main",
            "html_url": self.repo_url,
        }

    def make_github_response(self, data):
        """Build a GitHub HTTP response without making a network request."""
        response = requests.Response()
        response.status_code = 200
        response.url = "https://api.github.com/repos/example/site"
        response._content = json.dumps(data).encode("utf-8")
        return response

    def test_rejected_rechecks_preserve_saved_analysis_and_job(self):
        history_commits = []
        for commit_number in range(1, 52):
            history_commits.append({"sha": f"{commit_number:040x}"})
        first_history_page = self.make_github_response(history_commits[:50])
        first_history_page.headers["Link"] = (
            '<https://api.github.com/repos/example/site/commits?page=2>; rel="next"'
        )

        rejection_cases = [
            {
                "name": "history exceeds 50 commits",
                "history_responses": [
                    first_history_page,
                    self.make_github_response(history_commits[50:]),
                ],
                "tree_entries": [
                    {"path": "INDEX.HTML", "type": "blob", "mode": "100644"},
                ],
                "rejected_check": "history",
                "status_field": "history_status",
                "reason": "The default-branch history exceeds the 50-commit limit.",
            },
            {
                "name": "required root homepage is missing",
                "history_responses": [
                    self.make_github_response([{"sha": self.commit_sha}]),
                ],
                "tree_entries": [
                    {"path": "pages", "type": "tree", "mode": "040000"},
                    {"path": "pages/About.HTM", "type": "blob", "mode": "100644"},
                ],
                "rejected_check": "html",
                "status_field": "html_status",
                "reason": (
                    "The default branch must contain a regular root index.html file "
                    "(filename matching ignores case)."
                ),
            },
        ]

        for rejection_case in rejection_cases:
            with self.subTest(rejection=rejection_case["name"]):
                responses = [self.make_github_response(self.repository_data)]
                responses.extend(rejection_case["history_responses"])
                responses.extend([
                    self.make_github_response(self.repository_data),
                    self.make_github_response({
                        "commit": {"tree": {"sha": self.tree_sha}},
                    }),
                    self.make_github_response({
                        "sha": self.tree_sha,
                        "truncated": False,
                        "tree": rejection_case["tree_entries"],
                    }),
                ])
                self.mock_get.reset_mock()
                self.mock_get.side_effect = responses

                response = self.client.post(
                    reverse("check-repository-compatibility"),
                    {"url": self.repo_url},
                    format="json",
                )

                self.assertEqual(response.status_code, 200)
                report = response.json()
                self.assertEqual(report["overall_status"], "rejected")
                rejected_result = report[rejection_case["rejected_check"]]
                self.assertEqual(
                    rejected_result[rejection_case["status_field"]], "rejected"
                )
                self.assertEqual(rejected_result["reason"], rejection_case["reason"])
                self.assertIs(report["setup_available"], False)
                self.assertEqual(report["dependencies"]["status"], "pending")
                self.assertEqual(self.mock_get.call_count, len(responses))

                if rejection_case["rejected_check"] == "history":
                    self.assertEqual(report["html"]["html_status"], "passed")
                else:
                    self.assertEqual(report["history"]["history_status"], "passed")
                    self.assertEqual(report["html"]["html_pages"], ["pages/About.HTM"])

                # Full document equality includes IDs, links, timestamps and captures.
                for collection_name, saved_document in self.saved_documents.items():
                    collection = self.database[collection_name]
                    self.assertEqual(
                        collection.find_one({"_id": saved_document["_id"]}),
                        saved_document,
                        collection_name,
                    )
                    self.assertEqual(
                        collection.count_documents({}), 1, collection_name
                    )
