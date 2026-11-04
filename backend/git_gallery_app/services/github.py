from urllib.parse import urlparse

import requests

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
