import logging
import subprocess
import sys
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from ..models import Comparison
from .comparisons import claim_comparison

logger = logging.getLogger(__name__)

COMPARISON_TIMEOUT_SECONDS = 180
STALE_AFTER = timedelta(minutes=5)


def fail_comparison_attempt(comparison_id, attempt, code, message):
    return Comparison.objects.filter(
        pk=comparison_id,
        status=Comparison.Status.PROCESSING,
        attempts=attempt,
    ).update(
        status=Comparison.Status.FAILED,
        result=None,
        result_source=None,
        error_code=code,
        error_message=message,
        completed_at=timezone.now(),
    )


def process_next_comparison():
    #Go until we find something to process
    while True:
        comparison = (
            Comparison.objects
            .filter(status=Comparison.Status.QUEUED)
            .order_by("created_at", "pk")
            .first()
        )
        if comparison is None:
            return False

        attempt = claim_comparison(comparison)
        if attempt is not None:
            break

    logger.info(
        "Processing comparison %s (attempt %s)",
        comparison.pk,
        attempt,
    )
    code = "comparison_worker_failed"
    message = "Comparison processing stopped before a result was saved."

    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(settings.BASE_DIR / "manage.py"),
                "run_comparison",
                str(comparison.pk),
                str(attempt),
            ],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=COMPARISON_TIMEOUT_SECONDS,
        )

    except subprocess.TimeoutExpired:
        code = "comparison_timeout"
        message = "The comparison took too long and was stopped."

    except KeyboardInterrupt:
        fail_comparison_attempt(
            comparison.pk,
            attempt,
            "comparison_interrupted",
            "Comparison processing was interrupted.",
        )
        raise

    except OSError:
        logger.exception(
            "Could not start comparison %s",
            comparison.pk,
        )

    else:
        if completed.returncode != 0:
            logger.error(
                "Comparison %s exited with code %s: %s",
                comparison.pk,
                completed.returncode,
                completed.stderr,
            )

    # Only a still-processing record for this attempt is updated.
    fail_comparison_attempt(
        comparison.pk,
        attempt,
        code,
        message,
    )
    # Logging the outcome
    outcome = (
    Comparison.objects
    .filter(pk=comparison.pk, attempts=attempt)
    .values("status", "result_source", "error_code")
    .first()
    )

    if outcome is not None:
        log = (
            logger.warning
            if outcome["status"] == Comparison.Status.FAILED
            else logger.info
        )
        log(
            "Comparison %s attempt %d: status=%s source=%s error=%s",
            comparison.pk,
            attempt,
            outcome["status"],
            outcome["result_source"] or "-",
            outcome["error_code"] or "-",
        )
    return True


def recover_stale_comparisons():
    stale = Comparison.objects.filter(
        status=Comparison.Status.PROCESSING,
        started_at__lt=timezone.now() - STALE_AFTER,
    )

    failed = 0
    for comparison in stale:
        failed += fail_comparison_attempt(
            comparison.pk,
            comparison.attempts,
            "comparison_interrupted",
            "Comparison processing stopped before a result was saved.",
        )

    return failed