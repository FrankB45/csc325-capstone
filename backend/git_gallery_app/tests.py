from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from .models import Project
from .serializers import ProjectCreateSerializer, SavedAnalysisSerializer
from .views import project_analyses, project_detail, project_gallery


class ProjectCreateSerializerTests(SimpleTestCase):
    def setUp(self):
        self.project_data = {
            "project_name": "Portfolio",
            "repository_owner": "example",
            "repository_name": "portfolio",
            "repository_url": "https://github.com/example/portfolio",
        }

    def test_defaults_new_projects_to_not_started(self):
        serializer = ProjectCreateSerializer(data=self.project_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["analysis_status"],
            Project.AnalysisStatus.NOT_STARTED,
        )

    def test_rejects_processed_version_count_above_total(self):
        serializer = ProjectCreateSerializer(
            data={
                **self.project_data,
                "processed_versions": 2,
                "total_versions": 1,
            }
        )

        self.assertFalse(serializer.is_valid())

    def test_rejects_unknown_analysis_status(self):
        serializer = ProjectCreateSerializer(
            data={**self.project_data, "analysis_status": "unknown"}
        )

        self.assertFalse(serializer.is_valid())

    def test_saved_analysis_requires_results_and_valid_progress(self):
        serializer = SavedAnalysisSerializer(
            data={
                "analysis_status": "complete",
                "processed_versions": 3,
                "total_versions": 2,
                "results": {"captures": []},
            }
        )

        self.assertFalse(serializer.is_valid())


class ProjectGalleryApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def make_project(self, **overrides):
        values = {
            "pk": "project-id",
            "project_name": "Portfolio",
            "repository_owner": "example",
            "repository_name": "portfolio",
            "repository_url": "https://github.com/example/portfolio",
            "analysis_status": Project.AnalysisStatus.NOT_STARTED,
            "processed_versions": 0,
            "total_versions": 0,
            "saved_analyses": [],
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_gallery_is_available_without_sign_in(self):
        with patch("git_gallery_app.views.Project.objects.all", return_value=[]):
            response = project_gallery(self.factory.get("/api/projects/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"projects": [], "count": 0})

    def test_gallery_lists_repository_identity_and_status(self):
        project = self.make_project(
            analysis_status=Project.AnalysisStatus.PROCESSING,
            processed_versions=2,
            total_versions=5,
            saved_analyses=[{"id": "analysis-id"}],
        )
        with patch(
            "git_gallery_app.views.Project.objects.all",
            return_value=[project],
        ):
            response = project_gallery(self.factory.get("/api/projects/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["projects"][0],
            {
                "id": "project-id",
                "project_name": "Portfolio",
                "repository_owner": "example",
                "repository_name": "portfolio",
                "repository_url": "https://github.com/example/portfolio",
                "analysis_status": "processing",
                "processed_versions": 2,
                "total_versions": 5,
                "saved_analysis_count": 1,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        )

    def test_post_creates_shared_project(self):
        project = self.make_project()
        request = self.factory.post(
            "/api/projects/",
            {
                "project_name": "Portfolio",
                "repository_owner": "example",
                "repository_name": "portfolio",
                "repository_url": "https://github.com/example/portfolio",
            },
            format="json",
        )

        with patch(
            "git_gallery_app.models.Project.objects.get_or_create",
            return_value=(project, True),
        ):
            response = project_gallery(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["analysis_status"], "not_started")

    def test_post_reuses_existing_project(self):
        project = self.make_project(analysis_status=Project.AnalysisStatus.COMPLETE)
        request = self.factory.post(
            "/api/projects/",
            {
                "project_name": "Renamed Portfolio",
                "repository_owner": "example",
                "repository_name": "portfolio",
                "repository_url": "https://github.com/example/portfolio",
            },
            format="json",
        )

        with patch(
            "git_gallery_app.models.Project.objects.get_or_create",
            return_value=(project, False),
        ):
            response = project_gallery(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["analysis_status"], "complete")

    def test_project_status_can_be_updated_without_sign_in(self):
        project = self.make_project()
        project.save = Mock()
        request = self.factory.patch(
            "/api/projects/project-id/",
            {"analysis_status": "processing", "total_versions": 8},
            format="json",
        )

        with patch(
            "git_gallery_app.views.get_object_or_404",
            return_value=project,
        ):
            response = project_detail(request, "project-id")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["analysis_status"], "processing")
        self.assertEqual(response.data["total_versions"], 8)
        project.save.assert_called_once()

    def test_saved_analyses_are_readable_without_sign_in(self):
        saved_analysis = {
            "id": "analysis-id",
            "analysis_status": "complete",
            "processed_versions": 2,
            "total_versions": 2,
            "results": {"captures": [{"commit": "abc123", "screenshot": "/media/abc.png"}]},
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        project = self.make_project(saved_analyses=[saved_analysis])
        request = self.factory.get("/api/projects/project-id/analyses/")

        with patch(
            "git_gallery_app.views.get_object_or_404",
            return_value=project,
        ):
            response = project_analyses(request, "project-id")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"analyses": [saved_analysis], "count": 1})

    def test_saved_analysis_is_persisted_and_updates_project_status(self):
        project = self.make_project()
        project.save = Mock()
        request = self.factory.post(
            "/api/projects/project-id/analyses/",
            {
                "analysis_status": "partially_complete",
                "processed_versions": 1,
                "total_versions": 2,
                "results": {
                    "captures": [
                        {"commit": "abc123", "screenshot": "/media/abc.png"}
                    ]
                },
            },
            format="json",
        )

        with patch(
            "git_gallery_app.views.get_object_or_404",
            return_value=project,
        ):
            response = project_analyses(request, "project-id")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["analysis_status"], "partially_complete")
        self.assertEqual(len(project.saved_analyses), 1)
        self.assertEqual(
            project.saved_analyses[0]["results"]["captures"][0]["commit"],
            "abc123",
        )
        self.assertEqual(
            project.analysis_status,
            Project.AnalysisStatus.PARTIALLY_COMPLETE,
        )
        self.assertEqual(project.processed_versions, 1)
        self.assertEqual(project.total_versions, 2)
        project.save.assert_called_once()

    def test_saved_analysis_rejects_processed_count_above_total(self):
        project = self.make_project()
        request = self.factory.post(
            "/api/projects/project-id/analyses/",
            {
                "analysis_status": "complete",
                "processed_versions": 3,
                "total_versions": 2,
                "results": {},
            },
            format="json",
        )

        with patch(
            "git_gallery_app.views.get_object_or_404",
            return_value=project,
        ):
            response = project_analyses(request, "project-id")

        self.assertEqual(response.status_code, 400)
