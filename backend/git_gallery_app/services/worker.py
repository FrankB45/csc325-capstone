from ..models import Capture, Job

def final_status(captures: list[Capture]) -> str:
    """Decide a finished job's overall status from its captures.

    Every capture must already be COMPLETE or FAILED when this is called.
    """

    finished_statuses = {Capture.Status.COMPLETE, Capture.Status.FAILED}

    # Calling this too early is a bug in the worker, so fail loudly
    # instead of guessing an answer.
    if any(capture.status not in finished_statuses for capture in captures):
        raise ValueError("final_status() was called before every capture finished.")

    # create_job() never allows 0 captures, but be safe anyway.
    if not captures:
        return Job.Status.FAILED

    completed_count = sum(
        1 for capture in captures
        if capture.status == Capture.Status.COMPLETE
    )

    if completed_count == len(captures):
        return Job.Status.COMPLETE
    if completed_count > 0:
        return Job.Status.PARTIALLY_COMPLETE
    return Job.Status.FAILED