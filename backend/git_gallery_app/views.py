from django.shortcuts import get_object_or_404
import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response

import requests
from .models import Job, Project
from .serializers import ProjectCreateSerializer


from .services.github import (
    get_repository_compatibility_report,
    get_repository_information,
    parse_github_url,
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
    # Read the repository owner and name from its saved GitHub URL.
    try:
        repository_owner, repository_name = parse_github_url(
            project.repository_url
        )
    except ValueError:
        # Keep the rest of the gallery available if an older project
        # contains a URL that the parser doesn't recognize.
        repository_owner = None
        repository_name = None

    # Get the IDs of this project's repository snapshots.
    snapshot_ids = list(
        project.repository_snapshots.values_list("pk", flat=True)
    )

    # Find the most recently created job for those snapshots.
    latest_job = (
        Job.objects.filter(repo_snapshot_id__in=snapshot_ids)
        .order_by("-created_at", "-pk")
        .first()
    )

    return {
        "id": str(project.pk),
        "project_name": project.name,
        "repository_owner": repository_owner,
        "repository_name": repository_name,
        "repository_url": project.repository_url,
        "created_at": project.created_at.isoformat(),
        "latest_job": (
            {
                "id": str(latest_job.pk),
                "status": latest_job.status,
                "page_path": latest_job.page_path,
                "created_at": latest_job.created_at.isoformat(),
            }
            if latest_job is not None
            else None
        ),
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
