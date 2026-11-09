"""Capture one commit's page. Run as a child process by the worker:

    echo '<CaptureSpec as JSON>' | python -m git_gallery_app.capture.cli

Prints exactly ONE line of JSON to stdout:
    {"ok": true,  "blocked_urls": [...]}   screenshot saved to spec.out_path
    {"ok": false, "error": "..."}          a failure we can explain to the user
Any other problem is a bug: Python prints the traceback to stderr and exits non-zero.

Must NOT import Django.
"""
import contextlib
import json
import sys
from pathlib import Path

from .browser import screenshot_page
from .download import download_commit
from .errors import CaptureError
from .server import serve_directory
from .spec import CaptureSpec


def run_capture(spec: CaptureSpec) -> dict:
    """Capture into the temporary workspace supplied by the parent."""
    out_path = Path(spec.out_path)
    source_dir = out_path.parent / "source"
    source_dir.mkdir(parents=True)

    try:
        site = download_commit(spec.owner, spec.repo, spec.sha, source_dir)
        _check_page_exists(site, spec.page_path)

        with serve_directory(site) as base_url:
            blocked_urls = screenshot_page(
                base_url,
                spec.page_path,
                out_path,
                width=spec.width,
                height=spec.height,
                full_page=spec.full_page,
            )
    except CaptureError as error:
        return {"ok": False, "error": str(error)}

    return {"ok": True, "blocked_urls": blocked_urls}


def _check_page_exists(site, page_path):
    site = Path(site).resolve()
    page = (site / page_path).resolve()
    # create_job() only accepts known pages, so "../" here means a bug, not a user problem.
    if not page.is_relative_to(site):
        raise ValueError(f"page_path points outside the site folder: {page_path!r}")
    # Very common and legitimate: index.html exists today but not in early commits.
    if not page.is_file():
        raise CaptureError(f'The page "{page_path}" did not exist yet at this commit.')


def main() -> int:
    spec = CaptureSpec.from_json(sys.stdin.read())

    # stdout is reserved for our one JSON line. If anything inside prints,
    # send it to stderr instead so it can't corrupt the result.
    with contextlib.redirect_stdout(sys.stderr):
        result = run_capture(spec)

    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())