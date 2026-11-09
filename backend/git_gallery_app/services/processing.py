from collections.abc import Callable

from django.utils import timezone

from ..models import Job, Capture


def process_job(
    job: Job,
    capture_version: Callable[[Job, Capture], str],
) -> Job:
    """
    Process a claimed job.

    capture_version must save the screenshot and return its storage path,
    or raise an exception if that capture fails.
    """
    if job.status != Job.Status.PROCESSING:
        raise ValueError("The job must be claimed before processing.")

    if not job.captures:
        raise ValueError("The job must contain at least one capture.")

    for capture in job.captures:
        capture.status = Capture.Status.PROCESSING
        job.save(update_fields=["captures"])

        try:
            screenshot_path = capture_version(job, capture)

            if not isinstance(screenshot_path, str) or not screenshot_path:
                raise ValueError("Capture did not return a screenshot path.")

        except Exception as error:
            capture.status = Capture.Status.FAILED
            capture.error_message = str(error)

        else:
            capture.status = Capture.Status.COMPLETE
            capture.screenshot_path = screenshot_path

        capture.completed_at = timezone.now()
        job.save(update_fields=["captures"])

    successful_count = sum(
        capture.status == Capture.Status.COMPLETE
        for capture in job.captures
    )

    if successful_count == len(job.captures):
        job.status = Job.Status.COMPLETE
    elif successful_count > 0:
        job.status = Job.Status.PARTIALLY_COMPLETE
    else:
        job.status = Job.Status.FAILED

    job.completed_at = timezone.now()
    job.save(update_fields=["status", "completed_at"])

    return job