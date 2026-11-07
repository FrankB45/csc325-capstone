from django.test import SimpleTestCase

from .models import Capture, Job
from .services.worker import final_status


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