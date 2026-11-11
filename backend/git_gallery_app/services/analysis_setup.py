from django.utils.dateparse import parse_datetime

from ..commit_selection import validate_selection
from ..models import Commit, Project, RepositorySnapshot
from .dependencies import check_repository_dependencies
from .github import (
    _list_html_page_paths,
    get_branch_revision,
    get_commit_history,
    get_repository_information,
    parse_github_url,
)
from .jobs import create_job


class AnalysisSetupError(ValueError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def start_analysis(url, page_path, commit_shas, name=""):
    repository = get_repository_information(url)
    url = repository["url"]
    owner, repo = parse_github_url(url)

    revision = get_branch_revision(
        url,
        repository["default_branch"],
    )

    history = get_commit_history(url, ref=revision["head_sha"])
    selected = validate_selection(
        commit_shas,
        [item["sha"] for item in history],
    )

    pages = _list_html_page_paths(owner, repo, revision["tree_sha"])
    homepages = [
        path for path in pages
        if path.lower() == "index.html"
    ]

    if len(homepages) != 1:
        raise AnalysisSetupError(
            "The repository needs one root index.html."
        )

    if page_path not in pages:
        raise AnalysisSetupError(
            "The selected page is not in this snapshot."
        )

    dependencies = check_repository_dependencies(
        url,
        tree_sha=revision["tree_sha"],
    )

    if dependencies["dependency_status"] != "passed":
        raise AnalysisSetupError(
            dependencies["reason"],
            status_code=(
                502
                if dependencies["dependency_status"] == "unavailable"
                else 400
            ),
        )

    commits = [
        Commit(
            sha=item["sha"],
            message=item["message"],
            author_name=item["author_name"],
            committed_at=parse_datetime(item["date"]),
            position=position,
        )
        for position, item in enumerate(history)
    ]

    for commit in commits:
        commit.full_clean()

    project = Project(
        name=name or repository["name"],
        repository_url=url,
    )
    project.full_clean()

    snapshot = RepositorySnapshot(
        project=project,
        repository_url=url,
        default_branch=repository["default_branch"],
        head_sha=revision["head_sha"],
        commits=commits,
        available_pages=pages,
        default_page=homepages[0],
    )
    snapshot.full_clean(exclude=["project"])

    project.save()

    # Assign the relationship now that the project has an ID.
    snapshot.project = project
    snapshot.save()

    return create_job(snapshot, page_path, selected)