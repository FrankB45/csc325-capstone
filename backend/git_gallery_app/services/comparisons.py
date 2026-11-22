from ..comparison_schema import ComparisonResult
from .llm import request_image_comparison

import logging
import json 

from .diff_context import get_diff_context
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ..models import Capture, Comparison
from .llm import ( ComparisonRequestError, request_image_comparison, load_system_prompt )

logger = logging.getLogger(__name__)

UNVERIFIED_FILE_LIMITATION = (
    "A file reference could not be verified against the supplied patches."
)

def compare_screenshots(before_path, after_path, system_prompt, *, diff_context = ""):
    # Wrapper for LLM call 
    return request_image_comparison(
        before_path,
        after_path,
        system_prompt,
        result_type=ComparisonResult,  
        diff_context=diff_context,
    )


def finalize_result(result, context):
    """Apply the app's cleanup rules to a raw model comparison.

    1. A change's file_path is kept only if that file has a non-empty patch
       in the diff context (truncated patches still count). Otherwise it is
       set to None and a limitation note is added.
    2. The diff context's own limitations are appended after the model's.
    3. Exact duplicate limitations are removed, keeping first-seen order.

    Returns a new ComparisonResult. Neither argument is modified.
    """
    allowed_paths = {
        item["file_path"]
        for item in context["files"]
        if item["patch"]
    }

    changes = []
    cleanup_notes = []
    for change in result.changes:
        if change.file_path is not None and change.file_path not in allowed_paths:
            change = change.model_copy(update={"file_path": None})
            cleanup_notes.append(UNVERIFIED_FILE_LIMITATION)
        changes.append(change)

    limitations = list(dict.fromkeys([
        *result.limitations,
        *context["limitations"],
        *cleanup_notes,
    ]))

    return ComparisonResult(changes=changes, limitations=limitations)

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

def claim_comparison(comparison):
    # Attempt to claim a comparison for processing. 
    # Returns the new attempt number if successful, or None if another process claimed it first.
    attempt = comparison.attempts + 1

    updated = Comparison.objects.filter(
        pk=comparison.pk,
        status=Comparison.Status.QUEUED,
        attempts=comparison.attempts,
    ).update(
        status=Comparison.Status.PROCESSING,
        attempts=attempt,
        started_at=timezone.now(),
        completed_at=None,
        model_name=settings.OPENAI_MODEL,
        prompt_version="",
        result=None,
        result_source=None,
        error_code="",
        error_message="",
        llm_error=None,
    )

    return attempt if updated == 1 else None

def process_comparison(comparison_id, *, claimed_attempt=None):

    #pulls from db by comparison_id
    comparison = Comparison.objects.get(pk=comparison_id)

    # claimed_attempt is used when a retry occurs
    if claimed_attempt is None:
        # If the comparison is already processing we just return it 
        if comparison.status != Comparison.Status.QUEUED: 
            return comparison

        attempt = claim_comparison(comparison)
        # If we are unable to claim the comparison just return out
        if attempt is None:
            comparison.refresh_from_db()
            return comparison
    else:
        attempt = claimed_attempt
        # If the comparison is not in PROCESSING state or the attempt number does not match, we return it without processing
        if ( comparison.status != Comparison.Status.PROCESSING or comparison.attempts != attempt ): 
            return comparison

    # Now we can safely process the comparison, since we have claimed it for processing - Set Status PROCESSING
    active_attempt = Comparison.objects.filter(
        pk=comparison_id,
        status=Comparison.Status.PROCESSING,
        attempts=attempt,
    )

    outcome = {
        "status": Comparison.Status.FAILED,
        "result": None, 
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
        system_prompt, version = load_system_prompt() #load prompt here to capture any errors

        outcome["prompt_version"] = version
        # Load context from the git diff
        context = get_diff_context(
            comparison.capture_job.repo_snapshot.repository_url,
            before.commit_sha,
            after.commit_sha,
            page_path=comparison.capture_job.page_path,
        )

        raw_result = compare_screenshots(
            _screenshot_path(before),
            _screenshot_path(after),
            system_prompt,
            diff_context=json.dumps(context, ensure_ascii=False),
        )
        result = finalize_result(raw_result, context)
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
            result=result_data,
            result_source=Comparison.Source.LLM,
        )


    active_attempt.update(**outcome, completed_at=timezone.now())

    comparison.refresh_from_db()
    return comparison

class ComparisonRetryError(Exception):
    pass


def retry_comparison(comparison):
    """Takes a failed comparison and resets it to Queued"""
    if comparison.status != Comparison.Status.FAILED:
        raise ComparisonRetryError(
            "Only failed comparisons can be retried."
        )

    updated = Comparison.objects.filter(
        pk=comparison.pk,
        status=Comparison.Status.FAILED,
        attempts=comparison.attempts,
    ).update(
        status=Comparison.Status.QUEUED,
        result=None,
        result_source=None,
        model_name="",
        prompt_version="",
        error_code="",
        error_message="",
        llm_error=None,
        started_at=None,
        completed_at=None,
    )

    if updated != 1:
        raise ComparisonRetryError(
            "The comparison changed. Refresh its status and try again."
        )

    comparison.refresh_from_db()
    return comparison


