from ..models import Capture, Job
from django.urls import reverse


def get_project_details(project):
    result = {
        "id": str(project.pk),
        "name": project.name,
        "repository_url": project.repository_url,
        "created_at": project.created_at,
        "analysis": None,
    }

    job = (
        Job.objects
        .filter(repo_snapshot__project=project)
        .order_by("-created_at", "-pk")
        .first()
    )

    if job is None:
        return result

    snapshot = job.repo_snapshot
    commits_by_sha = {
        commit.sha: commit
        for commit in snapshot.commits
    }

    commits = []

    for capture in sorted(job.captures, key=lambda item: item.position):
        commit = commits_by_sha[capture.commit_sha]
        screenshot_url = None

        if (
            capture.status == Capture.Status.COMPLETE
            and capture.screenshot_path
        ):
            screenshot_url = reverse(
                "get-capture-image",
                kwargs={
                    "job_id": str(job.pk),
                    "position": capture.position,
                },
            )
        commits.append({
            "sha": commit.sha,
            "message": commit.message,
            "author_name": commit.author_name,
            "date": commit.committed_at,
            "position": capture.position,
            "status": capture.status,
            "error_message": capture.error_message,
            "screenshot_url": screenshot_url,
        })

    succeeded = sum(
        capture.status == Capture.Status.COMPLETE
        for capture in job.captures
    )
    failed = sum(
        capture.status == Capture.Status.FAILED
        for capture in job.captures
    )

    result["analysis"] = {
        "job_id": str(job.pk),
        "snapshot_id": str(snapshot.pk),
        "page_path": job.page_path,
        "status": job.status,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "progress": {
            "total": len(job.captures),
            "processed": succeeded + failed,
            "succeeded": succeeded,
            "failed": failed,
        },
        "commits": commits,
    }

    return result