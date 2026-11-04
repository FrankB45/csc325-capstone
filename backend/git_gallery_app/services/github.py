from urllib.parse import quote, urlparse

import requests

MAX_HISTORY_COMMITS = 50

def parse_github_url(url: str) -> tuple[str, str]:

    if not isinstance(url, str):
        raise ValueError("URL parser input must be a string.")

    parsed_url = urlparse(url)

    if parsed_url.scheme != "https":
        raise ValueError("Must be an HTTPS URL Format: github.com/owner/repo")
    if parsed_url.netloc.lower() != "github.com":
        raise ValueError("Must be a GitHub URL. Format: github.com/owner/repo")
    
    #pull out the important parts
    path = parsed_url.path.strip("/").split("/")
    if len(path) < 2:
        raise ValueError("URL must include both owner and repository name. Format: github.com/owner/repo")

    owner, repo = path[:2]
    return owner, repo


def get_repository_information(repo_url: str) -> dict:

    owner, repo = parse_github_url(repo_url)

    api_url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}"
    )

    response = requests.get(
        api_url,
        headers={"Accept": "application/vnd.github+json"},
        timeout=10,
    )

    MAX_SUPPORTED_COMMITS = 50


def get_commit_history(repo_url: str) -> list[dict]:
    """Commits on the default branch, ordered oldest -> newest.

    Each item: {"sha": <full 40-char sha>, "message": <first line>, "date": <ISO str>}.
    Raises ValueError if the repository has no commits or more than 50
    (the supported range), and requests exceptions on GitHub failures.
    """
    owner, repo = parse_github_url(repo_url)

    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits",
        headers={"Accept": "application/vnd.github+json"},
        # One extra so we can tell "exactly 50" from "more than 50".
        params={"per_page": MAX_SUPPORTED_COMMITS + 1},
        timeout=10,
    )

    if response.status_code == 409:  # GitHub: "Git Repository is empty."
        raise ValueError("Repository has no commits.")
    response.raise_for_status()
    items = response.json()

    if not items:
        raise ValueError("Repository has no commits.")
    if len(items) > MAX_SUPPORTED_COMMITS:
        raise ValueError(
            f"Repository has more than {MAX_SUPPORTED_COMMITS} commits, which is not supported."
        )

    # GitHub returns newest first; the app works oldest -> newest.
    return [
        {
            "sha": item["sha"],
            "message": item["commit"]["message"].splitlines()[0] if item["commit"]["message"] else "",
            "date": item["commit"]["author"]["date"],
        }
        for item in reversed(items)
    ]

    response.raise_for_status()
    data = response.json()

    return {
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data["description"],
        "default_branch": data["default_branch"],
        "url": data["html_url"],
    }


def check_repository_history(repo_url: str) -> dict:
    """Check history only; HTML-page and dependency checks are still required."""
    checking_commits = False

    try:
        repository = get_repository_information(repo_url)
        default_branch = repository["default_branch"]

        if default_branch is None or (
            isinstance(default_branch, str) and not default_branch.strip()
        ):
            return {
                "history_status": "rejected",
                "reason": "The repository has no usable default branch.",
            }

        if not isinstance(default_branch, str):
            return {
                "history_status": "unavailable",
                "reason": "GitHub returned invalid default-branch information. Try again.",
            }

        owner, repo = parse_github_url(repo_url)
        checking_commits = True
        commit_count = _count_default_branch_commits(owner, repo, default_branch)

    except requests.HTTPError as error:
        return _history_http_failure(error, checking_commits)
    except requests.RequestException:
        return {
            "history_status": "unavailable",
            "reason": "Could not retrieve usable data from GitHub. Try again.",
        }
    except (KeyError, TypeError):
        return {
            "history_status": "unavailable",
            "reason": "GitHub returned incomplete repository information. Try again.",
        }
    except ValueError as error:
        return {"history_status": "rejected", "reason": str(error)}

    if commit_count == 0:
        return {
            "history_status": "rejected",
            "reason": "The default branch has no commits. At least 1 commit is required.",
        }

    if commit_count > MAX_HISTORY_COMMITS:
        return {
            "history_status": "rejected",
            "reason": "The default-branch history exceeds the 50-commit limit.",
        }

    return {
        "history_status": "passed",
        "commit_count": commit_count,
        "reason": (
            "The default-branch history meets the 1–50 commit requirement. "
            "HTML-page and unsupported-dependency checks are still required."
        ),
    }


def _count_default_branch_commits(owner: str, repo: str, default_branch: str) -> int:
    """Count history pages, stopping once the supported limit is exceeded."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    commit_count = 0
    page_number = 1
    history_reference = default_branch

    while True:
        response = requests.get(
            api_url,
            headers={"Accept": "application/vnd.github+json"},
            params={
                "sha": history_reference,
                "per_page": MAX_HISTORY_COMMITS,
                "page": page_number,
            },
            timeout=10,
        )
        response.raise_for_status()
        commits = response.json()

        if not isinstance(commits, list):
            raise requests.RequestException("GitHub returned invalid commit history.")

        for commit in commits:
            if (
                not isinstance(commit, dict)
                or not isinstance(commit.get("sha"), str)
                or not commit["sha"].strip()
            ):
                raise requests.RequestException("GitHub returned invalid commit data.")

        commit_count += len(commits)
        if commit_count > MAX_HISTORY_COMMITS or "next" not in response.links:
            return commit_count

        if not commits:
            raise requests.RequestException("GitHub returned an empty history page.")

        # Keep later pages on the same history if the branch receives new commits.
        if page_number == 1:
            history_reference = commits[0]["sha"]
        page_number += 1


def _history_http_failure(error: requests.HTTPError, checking_commits: bool) -> dict:
    """Separate a missing history from an upstream request failure."""
    response = error.response
    status_code = response.status_code if response is not None else None

    if status_code == 404:
        reason = "Repository not found or not publicly accessible."
        if checking_commits:
            reason = "Default-branch history was not found or is no longer accessible."
        return {"history_status": "rejected", "reason": reason}

    if status_code == 409 and checking_commits:
        try:
            details = response.json()
        except ValueError:
            details = None
        if isinstance(details, dict) and details.get("message") == "Git Repository is empty.":
            return {
                "history_status": "rejected",
                "reason": "The repository has no commits. At least 1 commit is required.",
            }

    if status_code in (403, 429):
        reason = "GitHub denied the request or is limiting requests. Try again later."
    else:
        reason = "GitHub could not complete the history check. Try again."

    return {"history_status": "unavailable", "reason": reason}


def check_repository_html_pages(repo_url: str) -> dict:
    """Discover candidate filenames only, without deciding full compatibility."""
    try:
        owner, repo = parse_github_url(repo_url)
    except ValueError as error:
        return {"html_status": "rejected", "html_pages": [], "reason": str(error)}

    try:
        repository = get_repository_information(repo_url)
        default_branch = repository["default_branch"]

        if default_branch is None or (
            isinstance(default_branch, str) and not default_branch.strip()
        ):
            return {
                "html_status": "rejected",
                "html_pages": [],
                "reason": "The repository has no usable default branch.",
            }
        if not isinstance(default_branch, str):
            raise ValueError("GitHub returned invalid default-branch information.")

        tree_sha = _get_default_branch_tree_sha(owner, repo, default_branch)
        html_pages = _list_html_page_paths(owner, repo, tree_sha)

    except requests.HTTPError as error:
        response = error.response
        status_code = response.status_code if response is not None else None
        if status_code in (403, 429):
            reason = "GitHub denied the request or is limiting requests. Try again later."
        elif status_code == 404:
            reason = "The repository, default branch, or tree is not accessible. Try again."
        else:
            reason = "GitHub could not complete HTML-page discovery. Try again."
        return {"html_status": "unavailable", "html_pages": [], "reason": reason}
    except requests.RequestException:
        return {
            "html_status": "unavailable",
            "html_pages": [],
            "reason": "Could not retrieve usable data from GitHub. Try again.",
        }
    except (KeyError, TypeError):
        return {
            "html_status": "unavailable",
            "html_pages": [],
            "reason": "GitHub returned malformed repository or tree information. Try again.",
        }
    except ValueError as error:
        return {"html_status": "unavailable", "html_pages": [], "reason": str(error)}

    if not html_pages:
        return {
            "html_status": "rejected",
            "html_pages": [],
            "reason": "The default branch contains no candidate lowercase .html files.",
        }

    return {
        "html_status": "passed",
        "html_pages": html_pages,
        "reason": (
            "Candidate HTML filenames were found. Page rendering and full repository "
            "compatibility have not been checked; dependency checks are still required."
        ),
    }


def _get_default_branch_tree_sha(owner: str, repo: str, default_branch: str) -> str:
    """Resolve the branch to a fixed tree before listing its files."""
    # The heads/ prefix identifies the branch even if a tag has the same name.
    branch_reference = quote(f"heads/{default_branch}", safe="")
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits/{branch_reference}",
        headers={"Accept": "application/vnd.github+json"},
        timeout=10,
    )
    response.raise_for_status()
    tree_sha = response.json()["commit"]["tree"]["sha"]

    # A tree identifier must be a SHA, not another branch name that could move.
    if (
        not isinstance(tree_sha, str)
        or len(tree_sha) != 40
        or any(character not in "0123456789abcdef" for character in tree_sha)
    ):
        raise ValueError("GitHub returned an invalid default-branch tree identifier.")

    return tree_sha


def _list_html_page_paths(owner: str, repo: str, tree_sha: str) -> list[str]:
    """Return sorted candidate paths only when the entire tree listing is usable."""
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}",
        headers={"Accept": "application/vnd.github+json"},
        params={"recursive": "1"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("GitHub returned a malformed file listing.")
    if data.get("truncated") is True:
        raise ValueError("GitHub returned an incomplete file listing. Try again.")
    if (
        data.get("truncated") is not False
        or data.get("sha") != tree_sha
        or not isinstance(data.get("tree"), list)
    ):
        raise ValueError("GitHub returned a malformed file listing.")

    entry_types = {
        "100644": "blob",
        "100755": "blob",
        "040000": "tree",
        "120000": "blob",
        "160000": "commit",
    }
    html_pages = []
    for entry in data["tree"]:
        if not isinstance(entry, dict):
            raise ValueError("GitHub returned a malformed file entry.")

        path = entry.get("path")
        mode = entry.get("mode")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or any(part in ("", ".", "..") for part in path.split("/"))
            or not isinstance(mode, str)
            or mode not in entry_types
            or entry.get("type") != entry_types[mode]
        ):
            raise ValueError("GitHub returned a malformed file entry.")

        if mode in ("100644", "100755") and path.endswith(".html"):
            html_pages.append(path)

    return sorted(html_pages)


def get_repository_compatibility_report(repo_url: str) -> dict:
    """Combine prerequisite results without declaring full compatibility."""
    history_result = check_repository_history(repo_url)
    html_result = check_repository_html_pages(repo_url)
    history_status = history_result.get("history_status")
    html_status = html_result.get("html_status")

    # A known rejection takes precedence even if the other check is unavailable.
    if history_status == "rejected" or html_status == "rejected":
        overall_status = "rejected"
        reason = "An implemented check found a failed repository prerequisite."
    elif history_status != "passed" or html_status != "passed":
        overall_status = "unavailable"
        reason = "At least one implemented check could not complete reliably."
    else:
        overall_status = "pending"
        reason = (
            "History and candidate HTML checks passed; "
            "unsupported-dependency checking is unfinished."
        )

    return {
        "overall_status": overall_status,
        "reason": reason,
        "history": history_result,
        "html": html_result,
        "dependencies": {
            "status": "pending",
            "reason": "Unsupported-dependency checking is not implemented.",
        },
        "setup_available": False,
        # Each check resolves the default branch independently.
        "same_snapshot_guaranteed": False,
    }
