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

    response.raise_for_status()
    data = response.json()

    return {
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data["description"],
        "default_branch": data["default_branch"],
        "url": data["html_url"],
    }
