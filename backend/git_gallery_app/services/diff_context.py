import json
import re
from urllib.parse import quote

import requests

from .github import github_headers, parse_github_url

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_PATCH_CHARS = 8_000
MAX_CONTEXT_CHARS = 24_000
SOURCE_EXTENSIONS = (".html", ".htm", ".css", ".js", ".mjs")

# Given two commits from a repo
# Return Context to use for Comparison
def get_diff_context(repo_url, before_sha, after_sha, *, page_path):
    # Blank return context
    context = {
        "page_path": page_path,
        "before_sha": before_sha,
        "after_sha": after_sha,
        "files": [],
        "limitations": [],
    }

    try:
        if not all(
            isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha)
            for sha in (before_sha, after_sha)
        ):
            raise ValueError("Expected full commit SHAs.")

        owner, repo = parse_github_url(repo_url)
        url = (
            f"https://api.github.com/repos/"
            f"{quote(owner, safe='')}/{quote(repo, safe='')}/compare/"
            f"{before_sha}...{after_sha}"
        )

        with requests.get(
            url,
            headers=github_headers(),
            params={"page": 1, "per_page": 1},
            stream=True,
            timeout=(5, 10),
        ) as response:
            response.raise_for_status()
            payload = bytearray()

            for chunk in response.iter_content(chunk_size=64 * 1024):
                payload.extend(chunk)
                if len(payload) > MAX_RESPONSE_BYTES:
                    raise ValueError("GitHub comparison response is too large.")

            data = json.loads(payload)

        if not isinstance(data, dict) or not isinstance(data.get("files"), list):
            raise ValueError("Invalid comparison response.")

        merge_base = data.get("merge_base_commit")
        if not isinstance(merge_base, dict):
            raise ValueError("Missing comparison ancestry.")

        if merge_base.get("sha") != before_sha:
            context["limitations"] = [
                "Git diff omitted because its merge base differs from the "
                "before screenshot's commit. Only screenshots were compared."
            ]
            return context

        notes = set()
        files = data["files"]

        if len(files) >= 300:
            notes.add("GitHub's changed-file list may be incomplete.")

        candidates = []

        for item in files:
            if not isinstance(item, dict):
                raise ValueError("Invalid changed file.")

            name = item.get("filename")
            previous_name = item.get("previous_filename")
            status = item.get("status")
            patch = item.get("patch")

            if (
                not isinstance(name, str)
                or not isinstance(status, str)
                or (previous_name is not None and not isinstance(previous_name, str))
                or (patch is not None and not isinstance(patch, str))
            ):
                raise ValueError("Invalid changed-file details.")

            if not any(
                path.lower().endswith(SOURCE_EXTENSIONS)
                for path in (name, previous_name or "")
            ):
                notes.add("Source context includes only HTML, CSS, and JavaScript.")
                continue

            truncated = patch is not None and len(patch) > MAX_PATCH_CHARS

            if not patch:
                notes.add("Some changed source files have no available patch text.")

            if truncated:
                notes.add("Some source patches were shortened for the context limit.")

            candidates.append({
                "file_path": name,
                "previous_file_path": previous_name,
                "status": status,
                "patch": patch[:MAX_PATCH_CHARS] if patch is not None else None,
                "patch_truncated": truncated,
            })

        candidates.sort(key=lambda item: (
            page_path not in (item["file_path"], item["previous_file_path"]),
            item["file_path"],
        ))

        remaining = MAX_CONTEXT_CHARS
        selected = []

        for item in candidates:
            size = len(json.dumps(item, ensure_ascii=False)) + 2

            if size > remaining:
                notes.add("Some changed source files were omitted for the context limit.")
                continue

            selected.append(item)
            remaining -= size

        context["files"] = selected
        context["limitations"] = sorted(notes)

    except (requests.RequestException, ValueError, TypeError):
        context["files"] = []
        context["limitations"] = [
            "Git diff was unavailable; this comparison used screenshots only."
        ]

    return context