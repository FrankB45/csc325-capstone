from datetime import datetime, timezone
import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response

import requests

from .commit_selection import SelectionError, default_selection, validate_selection
from .services.analyses import save_analysis
from .services.github import get_commit_history, get_repository_information
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
    if not isinstance(request.data, dict):
        return Response({"error": "Send a JSON object."}, status=400)

    url = request.data.get("url")
    page_path = request.data.get("page_path")
    selected = request.data.get("commit_shas")

    if not url or not page_path:
        return Response(
            {"error": "url and page_path are required."},
            status=400,
        )

    try:
        history = get_commit_history(url)
    except (requests.RequestException, ValueError) as error:
        return _github_error(error)

    # Must be 1-10 distinct commits that belong to this repository's history.
    try:
        ordered = validate_selection(selected, [c["sha"] for c in history])
    except SelectionError as error:
        return Response({"error": error.message, "code": error.code}, status=400)

    # Snapshot of the exact full SHAs and their metadata, copied now, so later
    # changes to the repository never alter this analysis.
    by_sha = {c["sha"]: c for c in history}
    snapshot = {
        "url": url,
        "page_path": page_path,
        "commits": [by_sha[sha] for sha in ordered],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return Response(save_analysis(snapshot), status=201)
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
