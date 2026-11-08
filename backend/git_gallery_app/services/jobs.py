from ..models import RepositorySnapshot, Job, Capture
from django.utils import timezone
from datetime import timedelta

from django.db.models import Q

from .worker import final_status


# After creating a project and selecting the commits you want processed into images, 
# This function creates a job for processing the selected commits into images.
def create_job(
    repo_snapshot: RepositorySnapshot,
    page_path: str,
    commit_shas: list[str],
) -> Job:

    # Ensures the requested page is available in the repo
    if page_path not in repo_snapshot.available_pages:
        raise ValueError("The selected page is not available in this repository snapshot.")
    
    #Ensures the number of requested commits meets our restrictions
    if not 1 <= len(commit_shas) <= 10:
        raise ValueError("The number of requested commits must be between 1 and 10.")
    
    #Ensures unique commits
    if len(commit_shas) != len(set(commit_shas)):
        raise ValueError("The requested commits must be unique.")
    
    #Ensures all requested commits exist in the repo snapshot
    #Mapping of all commits in repo snapshot
    commits_by_sha = {
        commit.sha: commit
        for commit in repo_snapshot.commits
    }
    if any(sha not in commits_by_sha for sha in commit_shas):
        raise ValueError("One or more of the requested commits do not exist in this repository snapshot.")

    #Create a capture model for each requested commit
    selected_commits = sorted(
        [commits_by_sha[sha] for sha in commit_shas],
        key=lambda commit: commit.position,
    )
    captures = [
        Capture(commit_sha = commit.sha, position=position)
        for position, commit in enumerate(selected_commits)
    ]

    job = Job(
        repo_snapshot=repo_snapshot,
        page_path=page_path,
        captures=captures,
    )

    #Full Clean validates the model before saving it to the DB
    job.full_clean()
    job.save()

    return job

##########
# Used by background worker
# Finds the oldest queued job, marks it as processing and returns it
def claim_next_job() -> Job | None:
    while True:
        job = (
            Job.objects
            .filter(status=Job.Status.QUEUED)
            .order_by("created_at", "pk")
            .first()
        )
        if job is None:
            return None

        now = timezone.now()
        updated_count = Job.objects.filter(
            pk=job.pk,
            status=Job.Status.QUEUED,
        ).update(
            status=Job.Status.PROCESSING,
            started_at=now,
            heartbeat_at=now,
            attempts=job.attempts + 1,
        )
        if updated_count == 1:
            job.refresh_from_db()
            return job
        # If the job was not updated, it means another process claimed it

##########
# Used by the background worker when it starts (and every few minutes while it runs).
# Finds PROCESSING jobs whose worker stopped sending heartbeats, and either
# puts them back in the queue or, after too many attempts, gives up on them.

# Must be comfortably longer than one capture can take (CAPTURE_TIMEOUT_SECONDS = 120),
# because the heartbeat is only updated between captures.
STALE_AFTER = timedelta(minutes=5)
MAX_ATTEMPTS = 3
GAVE_UP_MESSAGE = "Processing was interrupted repeatedly, so this commit was not captured."


def recover_stale_jobs(now=None) -> tuple[int, int]:
    """Requeue or fail abandoned jobs. Returns (requeued_count, failed_count)."""
    now = now or timezone.now()
    cutoff = now - STALE_AFTER

    stale_jobs = Job.objects.filter(
        Q(heartbeat_at__lt=cutoff)
        # Jobs claimed before heartbeats existed only have started_at.
        | Q(heartbeat_at__isnull=True, started_at__lt=cutoff),
        status=Job.Status.PROCESSING,
    )

    requeued_count = failed_count = 0
    for job in stale_jobs:
        recover_job(job, now)
        job.save(update_fields=["status", "captures", "error_message", "completed_at"])
        if job.status == Job.Status.QUEUED:
            requeued_count += 1
        else:
            failed_count += 1
    return requeued_count, failed_count


def recover_job(job: Job, now) -> None:
    """Decide what happens to one abandoned job. Changes `job` in memory only."""
    # A capture that was running when the worker died never finished.
    for capture in job.captures:
        if capture.status == Capture.Status.PROCESSING:
            capture.status = Capture.Status.PENDING

    if job.attempts < MAX_ATTEMPTS:
        job.status = Job.Status.QUEUED
        return

    # Too many attempts: give up on what's left, but keep every finished screenshot.
    for capture in job.captures:
        if capture.status == Capture.Status.PENDING:
            capture.status = Capture.Status.FAILED
            capture.error_message = GAVE_UP_MESSAGE
            capture.completed_at = now
    job.status = final_status(job.captures)
    job.error_message = f"Processing stopped after {job.attempts} interrupted attempts."
    job.completed_at = now


##########
# Used by the background worker when processing a job ends early.

def release_job(job: Job) -> None:
    """Put a job this worker was processing back in the queue (deliberate shutdown)."""
    for capture in job.captures:
        if capture.status == Capture.Status.PROCESSING:
            capture.status = Capture.Status.PENDING
    job.status = Job.Status.QUEUED
    # A deliberate stop isn't a crash, so it shouldn't count toward MAX_ATTEMPTS.
    job.attempts = max(job.attempts - 1, 0)
    job.save(update_fields=["status", "captures", "attempts"])


def fail_job(job: Job, message: str, now=None) -> None:
    """Finish a job early because of an unexpected error, keeping finished screenshots."""
    now = now or timezone.now()
    for capture in job.captures:
        if capture.status in (Capture.Status.PENDING, Capture.Status.PROCESSING):
            capture.status = Capture.Status.FAILED
            capture.error_message = message
            capture.completed_at = now
    job.status = final_status(job.captures)
    job.error_message = message
    job.completed_at = now
    job.save(update_fields=["status", "captures", "error_message", "completed_at"])