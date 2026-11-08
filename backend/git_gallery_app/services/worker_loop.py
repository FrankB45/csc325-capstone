"""The background worker's main loop. Started by: python manage.py run_worker"""
import logging
import time

from .jobs import claim_next_job, fail_job, recover_stale_jobs, release_job
from .worker import UNEXPECTED_ERROR, process_job

logger = logging.getLogger(__name__)

POLL_SECONDS = 2                     # how often to check an empty queue
RECOVERY_INTERVAL_SECONDS = 5 * 60   # how often to look for abandoned jobs
ERROR_BACKOFF_SECONDS = 10           # how long to wait after an unexpected error


def work_once(process=process_job) -> bool:
    """Claim and process ONE job. Returns False if the queue was empty."""
    job = claim_next_job()
    if job is None:
        return False

    logger.info(
        "Processing job %s: %d capture(s), attempt %d",
        job.pk, len(job.captures), job.attempts,
    )
    try:
        process(job)
    except KeyboardInterrupt:
        # Ctrl+C (or SIGTERM, see the command): hand the job back, then keep stopping.
        logger.info("Stopping: putting job %s back in the queue", job.pk)
        release_job(job)
        raise
    except Exception:
        # A bug or unexpected failure in THIS job. Record it and move on to the next job.
        logger.exception("Job %s crashed; marking it failed", job.pk)
        fail_job(job, UNEXPECTED_ERROR)
    else:
        logger.info("Finished job %s: %s", job.pk, job.status)
    return True


def run_worker(poll_seconds=POLL_SECONDS, *, process=process_job,
               sleep=time.sleep, clock=time.monotonic, keep_running=lambda: True) -> None:
    """Process jobs forever. The keyword arguments exist so tests can control time."""
    logger.info("Worker started. Waiting for jobs... (Ctrl+C to stop)")
    _recover()
    last_recovery = clock()

    while keep_running():
        try:
            if clock() - last_recovery >= RECOVERY_INTERVAL_SECONDS:
                _recover()
                last_recovery = clock()

            did_work = work_once(process)
        except Exception:
            # Not a job problem. Probably MongoDB is unreachable. Don't crash; wait and retry.
            logger.exception("Worker error; retrying in %ss", ERROR_BACKOFF_SECONDS)
            sleep(ERROR_BACKOFF_SECONDS)
            continue

        if not did_work:
            sleep(poll_seconds)   # queue empty: wait a bit. Busy: go straight to the next job.


def _recover() -> None:
    requeued, failed = recover_stale_jobs()
    if requeued or failed:
        logger.warning("Recovered abandoned jobs: %d requeued, %d failed", requeued, failed)