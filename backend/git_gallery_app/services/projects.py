from ..models import Capture, Job, Project, RepositorySnapshot
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

def get_project_summaries():
    projects = list(Project.objects.order_by("-created_at", "-pk"))
    if not projects:
        return []

    snapshot_projects = dict(
        RepositorySnapshot.objects.filter(
            project_id__in=[project.pk for project in projects]
        ).values_list("pk", "project_id")
    )

    jobs = Job.objects.filter(
        repo_snapshot_id__in=list(snapshot_projects)
    ).order_by("-created_at", "-pk")

    latest_jobs = {}
    for job in jobs:
        project_id = snapshot_projects[job.repo_snapshot_id]
        latest_jobs.setdefault(project_id, job)

    return [
        _project_summary(project, latest_jobs.get(project.pk))
        for project in projects
    ]


def _project_summary(project, job):
    captures = job.captures if job else []

    succeeded = sum(
        c.status == Capture.Status.COMPLETE
        for c in captures
    )
    failed = sum(
        c.status == Capture.Status.FAILED
        for c in captures
    )

    thumbnail = max(
        (
            c for c in captures
            if c.status == Capture.Status.COMPLETE and c.screenshot_path
        ),
        key=lambda c: c.position,
        default=None,
    )

    activity_times = [project.created_at]

    if job:
        activity_times.extend(
            value for value in [
                job.created_at,
                job.started_at,
                job.completed_at,
                *[c.completed_at for c in captures],
            ]
            if value is not None
        )

    return {
        "id": str(project.pk),
        "name": project.name,
        "repository_url": project.repository_url,
        "updated_at": max(activity_times),
        "status": job.status if job else "not_started",
        "page_path": job.page_path if job else None,
        "progress": {
            "total": len(captures),
            "processed": succeeded + failed,
            "succeeded": succeeded,
            "failed": failed,
        },
        "thumbnail_url": (
            reverse(
                "get-capture-image",
                kwargs={
                    "job_id": str(job.pk),
                    "position": thumbnail.position,
                },
            )
            if thumbnail else None
        ),
    }