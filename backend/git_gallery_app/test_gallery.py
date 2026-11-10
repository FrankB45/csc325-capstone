from django.test import TestCase
from rest_framework.test import APIClient

from .models import Project


class SharedGalleryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_empty_gallery_returns_no_projects(self):
        response = self.client.get("/api/projects/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["projects"], [])

    def test_gallery_shows_project_and_repository_identity(self):
        Project.objects.create(
            name="My Portfolio",
            repository_url="https://github.com/example/portfolio",
        )

        response = self.client.get("/api/projects/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        project = response.data["projects"][0]
        self.assertEqual(project["project_name"], "My Portfolio")
        self.assertEqual(project["repository_owner"], "example")
        self.assertEqual(project["repository_name"], "portfolio")
        self.assertIsNone(project["latest_job"])