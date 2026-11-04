from datetime import datetime, timezone
from uuid import uuid4

from django.shortcuts import get_object_or_404
import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response

import requests
from .models import Project
from .serializers import (
    ProjectCreateSerializer,
    ProjectStatusSerializer,
    SavedAnalysisSerializer,
)
from .services.github import get_repository_information
from .services.github import (
    get_repository_compatibility_report,
    get_repository_information,
)

logger = logging.getLogger(__name__)


@api_view(["GET"])
def hello_world(request):
    return Response({"message": "Hello, Git Gallery!"})

@api_view(["POST"])
def get_repository(request):
    if not isinstance(request.data, dict):
        return Response(
            {"error": "Send a JSON object containing a url."},
            status=400,
        )
    
    url = request.data.get("url")

    try:
        
        repository = get_repository_information(url)

    except requests.HTTPError as error:
        if error.response.status_code == 404:
            return Response(
                {"error": "Repository not found or not publicly accessible."},
                status=404,
            )

        return Response(
            {"error": "GitHub could not complete the request."},
            status=502,
        )

    except requests.RequestException:
        return Response(
            {"error": "Could not retrieve data from GitHub. Try again."},
            status=502,
        )

    except ValueError as error:
        return Response(
            {"error": str(error)},
            status=400,
        )

    return Response(repository)


def serialize_project(project):
    return {
        "id": str(project.pk),
        "project_name": project.project_name,
        "repository_owner": project.repository_owner,
        "repository_name": project.repository_name,
        "repository_url": project.repository_url,
        "analysis_status": project.analysis_status,
        "processed_versions": project.processed_versions,
        "total_versions": project.total_versions,
        "saved_analysis_count": len(project.saved_analyses or []),
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


@api_view(["GET", "POST"])
def project_gallery(request):
    if request.method == "GET":
        projects = list(Project.objects.all())
        return Response({
            "projects": [serialize_project(project) for project in projects],
            "count": len(projects),
        })

    serializer = ProjectCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Project details are invalid.", "details": serializer.errors},
            status=400,
        )

    project = serializer.save()
    return Response(
        serialize_project(project),
        status=201 if serializer.created else 200,
    )


@api_view(["GET", "PATCH"])
def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    if request.method == "GET":
        return Response(serialize_project(project))

    serializer = ProjectStatusSerializer(
        project,
        data=request.data,
        partial=True,
        context={"project": project},
    )
    if not serializer.is_valid():
        return Response(
            {"error": "Project status is invalid.", "details": serializer.errors},
            status=400,
        )

    return Response(serialize_project(serializer.save()))


@api_view(["GET", "POST"])
def project_analyses(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    if request.method == "GET":
        saved_analyses = project.saved_analyses or []
        return Response({
            "analyses": saved_analyses,
            "count": len(saved_analyses),
        })

    serializer = SavedAnalysisSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Saved analysis is invalid.", "details": serializer.errors},
            status=400,
        )

    analysis = {
        "id": str(uuid4()),
        **serializer.validated_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    project.saved_analyses = [*(project.saved_analyses or []), analysis]
    project.analysis_status = analysis["analysis_status"]
    project.processed_versions = analysis["processed_versions"]
    project.total_versions = analysis["total_versions"]
    project.save()

    return Response(analysis, status=201)
@api_view(["POST"])
def check_repository_compatibility(request):
    """Return the existing compatibility report without enabling project setup."""
    # Let DRF handle JSON parsing errors before handling service failures below.
    data = request.data
    if not isinstance(data, dict):
        return Response({"error": "Send a JSON object containing a url."}, status=400)
    if "url" not in data:
        return Response({"error": "Include a url in the request."}, status=400)

    url = data["url"]
    if not isinstance(url, str):
        return Response({"error": "The url must be a string."}, status=400)
    url = url.strip()
    if not url:
        return Response({"error": "Enter a repository URL."}, status=400)

    try:
        report = get_repository_compatibility_report(url)
        overall_status = report["overall_status"]
        # A negative result is still a completed report, not a failed HTTP request.
        if overall_status in ("rejected", "pending"):
            return Response(report, status=200)
        elif overall_status == "unavailable":
            return Response(report, status=502)
        else:
            logger.error("The compatibility service returned an invalid report status.")
    except Exception:
        logger.exception("The compatibility report could not be produced.")

    return Response(
        {"error": "Could not complete the compatibility check. Try again."},
        status=500,
    )
