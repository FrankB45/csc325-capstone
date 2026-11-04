from ..models import RepositorySnapshot, Job, Capture
from django.utils import timezone


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

        updated_count = Job.objects.filter(
            pk=job.pk,
            status=Job.Status.QUEUED,
        ).update(
            status=Job.Status.PROCESSING,
            started_at=timezone.now(),
        )
        if updated_count == 1:
            job.refresh_from_db()
            return job
        # If the job was not updated, it means another process claimed it
