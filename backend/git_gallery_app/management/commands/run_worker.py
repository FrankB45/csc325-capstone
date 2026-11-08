import signal

from django.core.management.base import BaseCommand

from ...services.jobs import recover_stale_jobs
from ...services.worker_loop import POLL_SECONDS, run_worker, work_once


def _stop_on_sigterm(signum, frame):
    # `docker stop` and most process managers send SIGTERM instead of Ctrl+C.
    # Turning it into KeyboardInterrupt means both get the same clean shutdown.
    raise KeyboardInterrupt


class Command(BaseCommand):
    help = "Run the background worker that captures screenshots for queued jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--poll-seconds", type=float, default=POLL_SECONDS,
            help="How long to wait before checking again when the queue is empty.",
        )
        parser.add_argument(
            "--once", action="store_true",
            help="Process at most one job, then exit. Handy for debugging.",
        )

    def handle(self, *args, poll_seconds, once, **options):
        signal.signal(signal.SIGTERM, _stop_on_sigterm)
        try:
            if once:
                recover_stale_jobs()
                did_work = work_once()
                self.stdout.write("Processed one job." if did_work else "No queued jobs.")
            else:
                run_worker(poll_seconds)
        except KeyboardInterrupt:
            self.stdout.write("Worker stopped.")