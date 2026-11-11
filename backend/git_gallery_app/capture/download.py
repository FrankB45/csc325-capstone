"""Download one commit's files from GitHub and unpack them safely.

Runs inside the capture child process, so this module must NOT import Django.
"""
import io
import re
import tarfile
from pathlib import Path
from urllib.parse import quote

import requests

from .errors import CaptureError

# Safety limits. Your supported repos are small static sites, so these are generous.
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024     # the compressed .tar.gz
MAX_EXTRACTED_BYTES = 200 * 1024 * 1024   # all files after unpacking
MAX_FILES = 5_000

_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


def download_commit(owner: str, repo: str, sha: str, dest) -> Path:
    """Download the files of commit `sha` into the empty folder `dest`.

    Returns the folder that holds the site's files (GitHub wraps them in one
    top-level folder named "<repo>-<sha>").
    Raises CaptureError for problems the user should see.
    """
    dest = Path(dest)

    # These two are programmer errors (bugs in OUR code), so they're ValueError.
    if not _SHA_PATTERN.fullmatch(sha):
        raise ValueError(f"Not a full 40-character commit SHA: {sha!r}")
    if not dest.is_dir() or any(dest.iterdir()):
        raise ValueError(f"Destination must be an existing, empty folder: {dest}")

    url = (
        f"https://github.com/{quote(owner, safe='')}/{quote(repo, safe='')}"
        f"/archive/{sha}.tar.gz"
    )
    archive_bytes = _download(url)
    _extract(archive_bytes, dest)

    entries = list(dest.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        raise CaptureError("GitHub's download for this commit had an unexpected layout.")
    return entries[0]


def _download(url: str) -> bytes:
    """Fetch the archive, refusing to read more than MAX_DOWNLOAD_BYTES."""
    try:
        # stream=True: don't load the whole body at once; we read it chunk by chunk below.
        # timeout=(10, 60): give up if connecting takes >10s, or if no data arrives for 60s.
        response = requests.get(url, stream=True, timeout=(10, 60))
    except requests.RequestException as error:
        raise CaptureError("Could not reach GitHub to download this commit. Try again later.") from error

    with response:  # releases the network connection when we're done, even on errors
        if response.status_code == 404:
            raise CaptureError(
                "GitHub could not find this commit. It may have been removed, "
                "or the repository may no longer be public."
            )
        if response.status_code in (403, 429):
            raise CaptureError("GitHub is limiting downloads right now. Try again later.")
        if response.status_code != 200:
            raise CaptureError(
                f"GitHub returned an unexpected response (HTTP {response.status_code}) "
                "while downloading this commit."
            )

        buffer = io.BytesIO()
        try:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                buffer.write(chunk)
                if buffer.tell() > MAX_DOWNLOAD_BYTES:
                    raise CaptureError("This commit is too large to download.")
        except requests.RequestException as error:
            raise CaptureError("The download from GitHub was interrupted. Try again later.") from error

    return buffer.getvalue()


def _extract(archive_bytes: bytes, dest: Path) -> None:
    """Unpack the archive into dest, rejecting anything unsafe."""
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
            members = tar.getmembers()   # reads the list of files without writing any
            _check_limits(members)
            tar.extractall(dest, filter="data")
    # Order matters: FilterError is a *kind of* TarError, so it must be caught first.
    except tarfile.FilterError as error:
        raise CaptureError(
            "This commit contains a file path that is not allowed, such as one "
            "pointing outside the project folder."
        ) from error
    except (tarfile.TarError, EOFError) as error:
        raise CaptureError("GitHub's download for this commit could not be unpacked.") from error


def _check_limits(members: list[tarfile.TarInfo]) -> None:
    """Refuse archives that would unpack into something enormous."""
    if len(members) > MAX_FILES:
        raise CaptureError("This commit has too many files to capture.")
    total_bytes = sum(member.size for member in members if member.isfile())
    if total_bytes > MAX_EXTRACTED_BYTES:
        raise CaptureError("This commit is too large to unpack.")