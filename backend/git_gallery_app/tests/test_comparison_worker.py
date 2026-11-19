import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from ..models import Comparison
from ..services import comparison_worker as worker


class ComparisonWorkerTests(SimpleTestCase):
    def setUp(self):
        self.record = SimpleNamespace(
            pk="test-comparison",
            attempts=0,
        )
        selection = self.enterContext(
            patch.object(Comparison.objects, "filter")
        ).return_value
        self.first = selection.order_by.return_value.first
        self.first.return_value = self.record

        self.claim = self.enterContext(
            patch.object(worker, "claim_comparison", return_value=1)
        )
        self.run = self.enterContext(
            patch.object(worker.subprocess, "run")
        )
        self.fail = self.enterContext(
            patch.object(worker, "fail_comparison_attempt")
        )

    def test_empty_queue_does_not_start_process(self):
        self.first.return_value = None

        self.assertFalse(worker.process_next_comparison())
        self.run.assert_not_called()

    def test_lost_claim_does_not_start_process(self):
        self.first.side_effect = [self.record, None]
        self.claim.return_value = None

        self.assertFalse(worker.process_next_comparison())
        self.run.assert_not_called()

    def test_timeout_fails_the_claimed_attempt(self):
        self.run.side_effect = subprocess.TimeoutExpired(
            "comparison",
            180,
        )

        self.assertTrue(worker.process_next_comparison())
        self.assertEqual(self.run.call_args.kwargs["timeout"], 180)
        self.fail.assert_called_once_with(
            self.record.pk,
            1,
            "comparison_timeout",
            "The comparison took too long and was stopped.",
        )

    def test_shutdown_marks_interruption_and_stops(self):
        self.run.side_effect = KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            worker.process_next_comparison()

        self.fail.assert_called_once_with(
            self.record.pk,
            1,
            "comparison_interrupted",
            "Comparison processing was interrupted.",
        )