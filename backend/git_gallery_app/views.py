import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response

import requests
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
