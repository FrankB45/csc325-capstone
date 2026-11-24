import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response

import requests

from .commit_selection import SelectionError, default_selection, validate_selection
from .services.github import get_commit_history, get_repository_information
from .services.github import (
    get_repository_compatibility_report,
    get_repository_information,
)

from django.core.exceptions import ValidationError

from .serializers import (
    CreateAnalysisSerializer,
    CreatePageAnalysisSerializer,
    CreateComparisonSerializer,
    ComparisonSerializer,
)
from .services.analysis_setup import AnalysisSetupError, start_analysis, start_page_analysis

from bson import ObjectId
from bson.errors import InvalidId

from .models import Project, Capture, Job, Comparison
from .services.projects import ProjectBusyError, delete_project, get_project_details, get_project_summaries

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404

from .services.comparisons import ( ComparisonRetryError, get_or_create_comparison, retry_comparison, )

from .services.llm import ComparisonRequestError

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


def _github_error(error):
    """Same error mapping as get_repository, for the commit/analysis endpoints."""
    if isinstance(error, requests.HTTPError):
        if error.response.status_code == 404:
            return Response(
                {"error": "Repository not found or not publicly accessible."},
                status=404,
            )
        return Response(
            {"error": "GitHub could not complete the request."},
            status=502,
        )

    if isinstance(error, requests.RequestException):
        return Response(
            {"error": "Could not retrieve data from GitHub. Try again."},
            status=502,
        )

    return Response({"error": str(error)}, status=400)  # ValueError


@api_view(["POST"])
def get_commits(request):
    """Called when analysis setup opens: the commit list plus the preselected commits."""
    if not isinstance(request.data, dict):
        return Response(
            {"error": "Send a JSON object containing a url."},
            status=400,
        )

    try:
        commits = get_commit_history(request.data.get("url"))
    except (requests.RequestException, ValueError) as error:
        return _github_error(error)

    return Response(
        {
            "commits": commits,
            "preselected": default_selection([c["sha"] for c in commits]),
        }
    )


@api_view(["POST"])
def create_analysis(request):
    serializer = CreateAnalysisSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        job = start_analysis(**serializer.validated_data)

    except SelectionError as error:
        return Response(
            {"error": error.message, "code": error.code},
            status=400,
        )

    except AnalysisSetupError as error:
        return Response(
            {"error": str(error)},
            status=error.status_code,
        )

    except ValidationError as error:
        return Response({"error": error.messages}, status=400)

    except (requests.RequestException, ValueError) as error:
        return _github_error(error)

    return Response(
        {
            "job_id": str(job.pk),
            "project_id": str(job.repo_snapshot.project_id),
            "snapshot_id": str(job.repo_snapshot_id),
            "status": job.status,
            "total_captures": len(job.captures),
        },
        status=202,
    )

    
@api_view(["POST"])
def create_page_analysis(request, job_id):
    serializer = CreatePageAnalysisSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        job = start_page_analysis(job_id, serializer.validated_data["page_path"])
    except AnalysisSetupError as error:
        return Response({"error": str(error)}, status=error.status_code)
    except ValidationError as error:
        return Response({"error": error.messages}, status=400)

    return Response(
        {
            "job_id": str(job.pk),
            "project_id": str(job.repo_snapshot.project_id),
            "snapshot_id": str(job.repo_snapshot_id),
            "status": job.status,
            "total_captures": len(job.captures),
        },
        status=202,
    )


@api_view(["POST"])
def check_repository_compatibility(request):
    """Return the compatibility report and its limited-MVP setup decision."""
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
        # HTTP 200 means a report was returned; its status decides setup availability.
        if overall_status in ("accepted", "rejected", "pending"):
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

@api_view(["GET"])
def get_project(request, project_id):
    try:
        project = Project.objects.get(pk=ObjectId(project_id))
    except (InvalidId, Project.DoesNotExist):
        return Response(
            {"error": "Project not found."},
            status=404,
        )

    return Response(get_project_details(project))

@api_view(["GET"])
def get_capture_image(request, job_id, position):
    try:
        job = Job.objects.get(pk=ObjectId(job_id))
    except (InvalidId, Job.DoesNotExist):
        raise Http404("Job not found.")

    capture = next(
        (
            item
            for item in job.captures
            if item.position == position
        ),
        None,
    )

    if (
        capture is None
        or capture.status != Capture.Status.COMPLETE
        or not capture.screenshot_path
    ):
        raise Http404("Screenshot not available.")

    root = Path(settings.SCREENSHOT_ROOT).resolve()
    image_path = (root / capture.screenshot_path).resolve()

    if not image_path.is_relative_to(root):
        raise Http404("Screenshot not available.")

    try:
        image_file = image_path.open("rb")
    except (FileNotFoundError, IsADirectoryError):
        raise Http404("Screenshot file not found.")

    return FileResponse(
        image_file,
        content_type="image/png",
    )

@api_view(["GET"])
def get_projects(request):
    return Response({
        "projects": get_project_summaries(),
    })

@api_view(["GET", "DELETE"])
def get_project(request, project_id):
    try:
        project = Project.objects.get(pk=ObjectId(project_id))
    except (InvalidId, Project.DoesNotExist):
        return Response({"error": "Project not found."}, status=404)

    if request.method == "DELETE":
        try:
            delete_project(project)
        except ProjectBusyError as error:
            return Response({"error": str(error)}, status=409)
        return Response(status=204)

    return Response(get_project_details(project))

@api_view(["POST"])
def create_comparison(request, job_id):
    serializer = CreateComparisonSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        job = Job.objects.get(pk=ObjectId(job_id))
    except (InvalidId, Job.DoesNotExist):
        return Response({"error": "Job not found."}, status=404)

    try:
        comparison = get_or_create_comparison(
            job,
            **serializer.validated_data,
        )
    except ComparisonRequestError as error:
        return Response(
            {"error": str(error), "code": error.code},
            status=400,
        )

    pending = comparison.status in (
        Comparison.Status.QUEUED,
        Comparison.Status.PROCESSING,
    )

    return Response(
        ComparisonSerializer(comparison).data,
        status=202 if pending else 200,
    )


@api_view(["GET"])
def get_comparison(request, comparison_id):
    try:
        comparison = Comparison.objects.get(pk=ObjectId(comparison_id))
    except (InvalidId, Comparison.DoesNotExist):
        return Response({"error": "Comparison not found."}, status=404)

    return Response(ComparisonSerializer(comparison).data)


@api_view(["POST"])
def retry_comparison_view(request, comparison_id):
    try:
        comparison = Comparison.objects.get(pk=ObjectId(comparison_id))
        comparison = retry_comparison(comparison)
    except (InvalidId, Comparison.DoesNotExist):
        return Response({"error": "Comparison not found."}, status=404)
    except ComparisonRetryError as error:
        return Response({"error": str(error)}, status=409)

    return Response(
        ComparisonSerializer(comparison).data,
        status=202,
    )