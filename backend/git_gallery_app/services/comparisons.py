from pydantic import BaseModel, ConfigDict
from .llm import request_image_comparison

import logging
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, ConfigDict

from ..models import Capture, Comparison
from .llm import ( ComparisonRequestError, request_image_comparison )

logger = logging.getLogger(__name__)


class ComparisonChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element: str | None
    location: str | None
    file_path: str | None
    description: str


class ComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: list[ComparisonChange]
    limitations: list[str]

def compare_screenshots(before_path, after_path):
    # Wrapper for LLM call 
    return request_image_comparison(
        before_path,
        after_path,
        result_type=ComparisonResult,
    )

def _get_captures(job, before_position, after_position):
    #get all the captures from a job and pull out the before and after
    captures = {
        capture.position: capture for capture in job.captures
    }

    before = captures.get(before_position)
    after = captures.get(after_position)

    if any( capture is None 
            or capture.status != Capture.Status.COMPLETE
            or not capture.screenshot_path
            for capture in (before, after) ):
                raise ComparisonRequestError(
                    "captures_unavailable",
                    "The requested screenshots are not available."
                )
    
    return before, after

def _screenshot_path(capture):
    #Given a capture, return the absolute path to the screenshot file. Raises ComparisonRequestError if the file is not available or cannot be read.
    root = Path(settings.SCREENSHOT_ROOT).resolve()
    path = (root / capture.screenshot_path).resolve()

    if not path.is_relative_to(root):
        raise ComparisonRequestError(
            "image_unavailable",
            "A saved screenshot could not be read.",
        )

    return path

def get_or_create_comparison(job, first_position, second_position):
    if( type(first_position) is not int
        or type(second_position) is not int
        or first_position == second_position ):
            raise ComparisonRequestError(
                "invalid_positions",
                "The requested positions are invalid."
            )

    # Normalize & Sort Comparison to prevent associative duplicates
    before_position, after_position = sorted(
        (first_position, second_position)
    )

    lookup = {
        "capture_job": job,
        "before_position": before_position,
        "after_position": after_position,
    }

    # Checks to see if we already have a comparison for this pair of commits
    existing = Comparison.objects.filter(**lookup).first()

    if existing is not None:
        return existing

    # If not, we create the compare and return
    # if there is an issue (captures not associaed with job) then fail
    _get_captures(job, before_position, after_position)

    comparison, _created = Comparison.objects.get_or_create(**lookup)

    return comparison


def process_comparison(comparison_id):

    #pulls from db by comparison_id
    comparison = Comparison.objects.get(pk=comparison_id)

    #completed, failed or processing are returned (dont need processing)
    if comparison.status != Comparison.Status.QUEUED:
        return comparison

    #keep track of the processing attempts
    attempt = comparison.attempts + 1

    # Try to claim this comparison for processing
    claimed = Comparison.objects.filter(
        pk=comparison_id,
        status=Comparison.Status.QUEUED,
        attempts=Comparison.attempts,
    ).update(
        status=Comparison.Status.PROCESSING,
        attempts=attempt,
        started_at=timezone.now(),
        completed_at=None,
        model_name=settings.OPENAI_MODEL,
        prompt_version=settings.SYSTEM_PROMPT_VERSION,
        result=None,
        result_source=None,
        error_code="",
        error_message="",
        llm_error=None,
    )

    if claimed == 0:
        # Another process claimed this comparison first, so we just return it
        comparison.refresh_from_db()
        return comparison

    # Now we can safely process the comparison, since we have claimed it for processing - Set Status PROCESSING
    active_attempt = Comparison.objects.filter(
        pk=comparison_id,
        status=Comparison.Status.PROCESSING,
        attempts=attempt,
    )

    outcome = {
        "status": Comparison.status.FAILED,
        "results": None, 
        "result_source": None,
        "error_code": "",
        "error_message": "",
        "llm_error": None,
    }

    try: 

        # Get the captures for the before and after positions
        before, after = _get_captures(
            comparison.capture_job,
            comparison.before_position,
            comparison.after_position,
        )
        # Here we actually perform the comparison by calling the LLM service
        result = compare_screenshots(
            _screenshot_path(before),
            _screenshot_path(after),
        )

        result_data = result.model_dump(mode="json")

    except ComparisonRequestError as error:
        outcome["error_code"] = error.code
        outcome["error_message"] = str(error)

        # Preflight errors have an error but no failed llm response
        if error.code.startswith("openai_") or error.code in {"incomplete_response","refused_response","invalid_response"}:
            outcome["llm_error"] = {
                "code": error.code,
                "message": str(error),
            }
    except Exception:
        logger.exception("Unknown/unexpected error while processing comparison: %s", comparison.pk)

        outcome["error_code"] = "comparison_failed_unknown_error"
        outcome["error_message"] = "An unknown error occurred while processing the comparison."
    
    else:
        outcome.update(
            status=Comparison.Status.COMPLETE,
            results=result_data,
            result_source=Comparison.Source.LLM,
        )


    active_attempt.update(**outcome, completed_at=timezone.now())

    comparison.refresh_from_db()
    return comparison




