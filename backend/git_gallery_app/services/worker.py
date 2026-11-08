import json
import logging
import subprocess
import sys
from dataclasses import asdict

from django.conf import settings
from django.utils import timezone

from ..capture.spec import CaptureSpec
from ..models import Capture, Job
from .github import parse_github_url

logger = logging.getLogger(__name__)

# Generous: download (up to 60s of silence) + page load (30s) + screenshot (30s).
CAPTURE_TIMEOUT_SECONDS = 120

# Shown to users when the child crashed. The real details go to the log, never the UI.
UNEXPECTED_ERROR = "Something went wrong while capturing this commit."
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

def run_capture_in_child(spec: CaptureSpec) -> dict:
    """Run one capture in a separate process. ALWAYS returns {"ok": ..., ...}.

    Turns every way the child can go wrong (hang, crash, garbage output)
    into a normal failed result, so process_job never has to care how it failed.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "git_gallery_app.capture.cli"],
            input=json.dumps(asdict(spec)),   # the spec goes in on stdin
            capture_output=True,              # collect stdout and stderr instead of printing them
            text=True,                        # str instead of bytes
            timeout=CAPTURE_TIMEOUT_SECONDS,  # kill the child if it runs longer than this
            cwd=settings.BASE_DIR,            # backend/, so "-m git_gallery_app..." can be found
        )
    except subprocess.TimeoutExpired:
        logger.warning("Capture of %s timed out after %ss", spec.sha, CAPTURE_TIMEOUT_SECONDS)
        return {"ok": False, "error": "This capture took too long and was stopped."}

    if result.returncode != 0:
        logger.error(
            "Capture child for %s exited with code %s. stderr:\n%s",
            spec.sha, result.returncode, result.stderr,
        )
        return {"ok": False, "error": UNEXPECTED_ERROR}

    try:
        outcome = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error("Capture child for %s printed invalid JSON: %r", spec.sha, result.stdout)
        return {"ok": False, "error": UNEXPECTED_ERROR}

    if not isinstance(outcome, dict) or not isinstance(outcome.get("ok"), bool):
        logger.error("Capture child for %s printed an unexpected result: %r", spec.sha, outcome)
        return {"ok": False, "error": UNEXPECTED_ERROR}

    return outcome


def process_job(job: Job, run_capture=run_capture_in_child) -> None:
    """Capture every commit in a claimed job, saving progress after each step."""
    owner, repo = parse_github_url(job.repo_snapshot.repository_url)

    for capture in job.captures:
        # Finished captures are final. This lets a requeued job resume where it left off.
        if capture.status in (Capture.Status.COMPLETE, Capture.Status.FAILED):
            continue

        # 1. Tell the world this capture is running, and clear leftovers from any earlier attempt.
        capture.status = Capture.Status.PROCESSING
        capture.error_message = ""
        capture.screenshot_path = ""
        _save_progress(job)

        # 2. Run it.
        relative_path = f"{job.pk}/{capture.position:02d}-{capture.commit_sha[:7]}.png"
        spec = CaptureSpec(
            owner=owner,
            repo=repo,
            sha=capture.commit_sha,
            page_path=job.page_path,
            out_path=str(settings.SCREENSHOT_ROOT / relative_path),
            width=job.viewport_width,
            height=job.viewport_height,
            full_page=job.full_page,
        )
        outcome = run_capture(spec)

        # 3. Record the result.
        if outcome["ok"]:
            capture.status = Capture.Status.COMPLETE
            capture.screenshot_path = relative_path
        else:
            capture.status = Capture.Status.FAILED
            capture.error_message = outcome.get("error") or UNEXPECTED_ERROR
        capture.completed_at = timezone.now()
        _save_progress(job)

    job.status = final_status(job.captures)
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "completed_at"])


def _save_progress(job: Job) -> None:
    # Every progress save doubles as a heartbeat: "this worker is still alive".
    job.heartbeat_at = timezone.now()
    job.save(update_fields=["captures", "heartbeat_at"])