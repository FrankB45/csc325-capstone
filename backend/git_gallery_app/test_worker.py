from django.test import SimpleTestCase

from .models import Capture, Job
from .services.worker import final_status

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from .capture.spec import CaptureSpec
from .services.worker import run_capture_in_child

class CaptureProcessTests(SimpleTestCase):
    def test_timeout_removes_downloads_and_partial_image(self):
        def simulate_timeout(*args, **kwargs):
            payload = json.loads(kwargs["input"])
            image = Path(payload["out_path"])

            source = image.parent / "source"
            source.mkdir()
            (source / "index.html").write_text("Downloaded page")
            image.write_bytes(b"incomplete image")

            raise subprocess.TimeoutExpired(args[0], timeout=1)

        with TemporaryDirectory() as folder:
            spec = CaptureSpec(
                owner="example",
                repo="demo",
                sha="a" * 40,
                page_path="index.html",
                out_path=str(Path(folder) / "finished.png"),
                width=800,
                height=600,
                full_page=True,
            )

            with patch(
                "git_gallery_app.services.worker.subprocess.run",
                side_effect=simulate_timeout,
            ):
                outcome = run_capture_in_child(spec)

            self.assertFalse(outcome["ok"])
            self.assertIn("too long", outcome["error"])
            self.assertEqual(list(Path(folder).iterdir()), [])

            
def make_captures(*statuses):
    """Build in-memory captures (nothing is saved) with the given statuses."""
    return [
        Capture(commit_sha=f"{position:040x}", position=position, status=status)
        for position, status in enumerate(statuses)
    ]


COMPLETE = Capture.Status.COMPLETE
FAILED = Capture.Status.FAILED


class FinalStatusTests(SimpleTestCase):
    def test_all_complete_is_complete(self):
        captures = make_captures(COMPLETE, COMPLETE, COMPLETE)
        self.assertEqual(final_status(captures), Job.Status.COMPLETE)

    def test_mixed_results_are_partially_complete(self):
        captures = make_captures(COMPLETE, FAILED, COMPLETE)
        self.assertEqual(final_status(captures), Job.Status.PARTIALLY_COMPLETE)

    def test_all_failed_is_failed(self):
        captures = make_captures(FAILED, FAILED)
        self.assertEqual(final_status(captures), Job.Status.FAILED)

    def test_single_capture(self):
        self.assertEqual(final_status(make_captures(COMPLETE)), Job.Status.COMPLETE)
        self.assertEqual(final_status(make_captures(FAILED)), Job.Status.FAILED)

    def test_unfinished_capture_raises(self):
        for unfinished in (Capture.Status.PENDING, Capture.Status.PROCESSING):
            with self.subTest(status=unfinished):
                with self.assertRaises(ValueError):
                    final_status(make_captures(COMPLETE, unfinished))