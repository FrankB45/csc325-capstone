from django.test import TestCase
from rest_framework.test import APIClient

from .models import Job, Project, RepositorySnapshot


class SharedGalleryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_empty_gallery_returns_no_projects(self):
        response = self.client.get("/api/projects/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["projects"], [])

    def test_gallery_shows_project_and_repository_identity(self):
        Project.objects.create(
            name="My Portfolio",
            repository_url="https://github.com/example/portfolio",
        )

        response = self.client.get("/api/projects/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["projects"]), 1)

        project = response.data["projects"][0]
        self.assertEqual(project["name"], "My Portfolio")
        self.assertEqual(project["repository_owner"], "example")
        self.assertEqual(project["repository_name"], "portfolio")
        self.assertIsNone(project["status"])
        self.assertIsNone(project["job_id"])

    def test_gallery_shows_latest_job_status(self):
        project = Project.objects.create(
            name="My Portfolio",
            repository_url="https://github.com/example/portfolio",
        )

        snapshot = RepositorySnapshot.objects.create(
            project=project,
            repository_url=project.repository_url,
            default_branch="main",
            head_sha="a" * 40,
            available_pages=["index.html"],
            default_page="index.html",
        )

        job = Job.objects.create(
            repo_snapshot=snapshot,
            page_path="index.html",
            status=Job.Status.PROCESSING,
        )

        response = self.client.get("/api/projects/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["projects"]), 1)

        summary = response.data["projects"][0]
        self.assertEqual(summary["job_id"], str(job.pk))
        self.assertEqual(summary["status"], Job.Status.PROCESSING)
        self.assertEqual(summary["page_path"], "index.html")
