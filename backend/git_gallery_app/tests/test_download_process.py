import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from ..capture.download import download_commit   # ".." versions if your tests are in tests/
from ..capture.errors import CaptureError

SHA = "a" * 40


def make_tarball(files, top_folder=f"demo-{SHA}"):
    """Build a .tar.gz in memory. `files` maps path -> text content.

    By default everything goes inside one top folder, like GitHub's real archives.
    Pass top_folder="" to put entries at the top level (useful for bad archives).
    """
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(f"{top_folder}/{name}" if top_folder else name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeResponse:
    """Stands in for requests' Response, with only the parts download.py uses."""

    def __init__(self, status_code=200, body=b"", fail_midway=False):
        self.status_code = status_code
        self._body = body
        self._fail_midway = fail_midway

    def iter_content(self, chunk_size):
        for start in range(0, len(self._body), chunk_size):
            if self._fail_midway and start > 0:
                raise requests.ConnectionError("connection dropped")
            yield self._body[start:start + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class DownloadCommitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dest = Path(temp.name)

        # Replace requests.get *as download.py sees it*, so no test touches the internet.
        get_patch = patch("git_gallery_app.capture.download.requests.get")
        self.mock_get = get_patch.start()
        self.addCleanup(get_patch.stop)

    def respond_with(self, **kwargs):
        self.mock_get.return_value = FakeResponse(**kwargs)

    def assert_capture_error(self, expected_words):
        with self.assertRaises(CaptureError) as caught:
            download_commit("example", "demo", SHA, self.dest)
        self.assertIn(expected_words, str(caught.exception))

    # --- the happy path ---

    def test_downloads_and_unpacks_the_commit(self):
        self.respond_with(body=make_tarball({"index.html": "<h1>Hi</h1>", "css/style.css": "h1 {}"}))

        root = download_commit("example", "demo", SHA, self.dest)

        self.assertEqual((root / "index.html").read_text(), "<h1>Hi</h1>")
        self.assertEqual((root / "css" / "style.css").read_text(), "h1 {}")
        url = self.mock_get.call_args.args[0]
        self.assertEqual(url, f"https://github.com/example/demo/archive/{SHA}.tar.gz")

    # --- programmer errors: caught before any network call ---

    def test_rejects_bad_sha_without_downloading(self):
        for bad_sha in ("main", "abc123", "A" * 40, SHA + "/../x"):
            with self.subTest(sha=bad_sha):
                with self.assertRaises(ValueError):
                    download_commit("example", "demo", bad_sha, self.dest)
        self.mock_get.assert_not_called()

    def test_rejects_non_empty_destination(self):
        (self.dest / "leftover.txt").write_text("old")
        with self.assertRaises(ValueError):
            download_commit("example", "demo", SHA, self.dest)
        self.mock_get.assert_not_called()

    # --- GitHub and network problems ---

    def test_missing_commit(self):
        self.respond_with(status_code=404)
        self.assert_capture_error("could not find this commit")

    def test_rate_limited(self):
        for status in (403, 429):
            with self.subTest(status=status):
                self.respond_with(status_code=status)
                self.assert_capture_error("limiting downloads")

    def test_unexpected_status(self):
        self.respond_with(status_code=500)
        self.assert_capture_error("HTTP 500")

    def test_network_failure(self):
        self.mock_get.side_effect = requests.ConnectionError("no internet")
        self.assert_capture_error("Could not reach GitHub")

    def test_download_interrupted(self):
        # 200 KB arrives as several 64 KB chunks; the fake drops after the first.
        self.respond_with(body=b"x" * 200_000, fail_midway=True)
        self.assert_capture_error("interrupted")

    # --- size limits (patched small so we don't need huge test files) ---

    def test_download_too_large(self):
        self.respond_with(body=make_tarball({"index.html": "x" * 5000}))
        with patch("git_gallery_app.capture.download.MAX_DOWNLOAD_BYTES", 10):
            self.assert_capture_error("too large to download")

    def test_unpacked_size_too_large(self):
        self.respond_with(body=make_tarball({"index.html": "x" * 5000}))
        with patch("git_gallery_app.capture.download.MAX_EXTRACTED_BYTES", 100):
            self.assert_capture_error("too large to unpack")

    def test_too_many_files(self):
        self.respond_with(body=make_tarball({f"page{n}.html": "" for n in range(5)}))
        with patch("git_gallery_app.capture.download.MAX_FILES", 3):
            self.assert_capture_error("too many files")

    # --- unsafe or broken archives ---

    def test_blocks_paths_outside_the_folder(self):
        self.respond_with(body=make_tarball({"../../evil.txt": "gotcha"}, top_folder=""))
        self.assert_capture_error("not allowed")
        self.assertFalse((self.dest.parent / "evil.txt").exists())

    def test_corrupt_archive(self):
        self.respond_with(body=b"this is not a tarball")
        self.assert_capture_error("could not be unpacked")

    def test_unexpected_layout(self):
        self.respond_with(body=make_tarball({"index.html": "<h1>Hi</h1>"}, top_folder=""))
        self.assert_capture_error("unexpected layout")