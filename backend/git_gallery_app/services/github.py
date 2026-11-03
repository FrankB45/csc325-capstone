from urllib.parse import urlparse

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
