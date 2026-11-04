from django.test import TestCase

from django.test import TransactionTestCase
from django.utils import timezone

from .models import Project, RepositorySnapshot, Commit, Job, Capture
from .services.jobs import create_job, claim_next_job

from datetime import timedelta


##########
# Tests for the Job functionality

class JobTests(TransactionTestCase):
    def setUp(self):
        project = Project.objects.create(
            name="Test project",
            repository_url="https://github.com/example/demo",
        )

        # Eleven distinct, synthetic commit SHAs.
        self.shas = [f"{number:040x}" for number in range(1, 12)]

        self.snapshot = RepositorySnapshot.objects.create(
            project=project,
            repository_url=project.repository_url,
            default_branch="main",
            head_sha=self.shas[-1],
            commits=[
                Commit(
                    sha=sha,
                    message=f"Commit {position}",
                    author_name="Test Author",
                    committed_at=timezone.now(),
                    position=position,
                )
                for position, sha in enumerate(self.shas)
            ],
            available_pages=["index.html", "about.html"],
            default_page="index.html",
        )

        # Use the snapshot as loaded from MongoDB.
        self.snapshot.refresh_from_db()

##########
# Tests for the create_job function

    def test_saves_job_in_history_order(self):
        job = create_job(
            self.snapshot,
            "about.html",
            [self.shas[8], self.shas[2], self.shas[5]],
        )

        saved_job = Job.objects.get(pk=job.pk)

        self.assertEqual(saved_job.repo_snapshot_id, self.snapshot.pk)
        self.assertEqual(saved_job.page_path, "about.html")
        self.assertEqual(saved_job.status, Job.Status.QUEUED)

        self.assertEqual(
            [capture.commit_sha for capture in saved_job.captures],
            [self.shas[2], self.shas[5], self.shas[8]],
        )

        self.assertEqual(
            [capture.position for capture in saved_job.captures],
            [0, 1, 2],
        )

        for capture in saved_job.captures:
            self.assertEqual(capture.status, Capture.Status.PENDING)

    def test_accepts_one_and_ten_commits(self):
        for count in [1, 10]:
            with self.subTest(count=count):
                job = create_job(
                    self.snapshot,
                    "index.html",
                    self.shas[:count],
                )

                saved_job = Job.objects.get(pk=job.pk)
                self.assertEqual(len(saved_job.captures), count)

    def test_invalid_selections_do_not_create_jobs(self):
        cases = [
            ("missing page", "missing.html", [self.shas[0]]),
            ("no commits", "index.html", []),
            ("too many commits", "index.html", self.shas),
            ("duplicate commits", "index.html", [self.shas[0]] * 2),
            ("unknown commit", "index.html", ["f" * 40]),
        ]

        for label, page_path, commit_shas in cases:
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    create_job(self.snapshot, page_path, commit_shas)

                self.assertEqual(Job.objects.count(), 0)

##########
# Tests for the claim_next_job function (Still Inside Job Tests to reuse setup)

    def test_claim_returns_none_when_queue_is_empty(self):
        self.assertIsNone(claim_next_job())

    def test_claim_marks_job_as_processing(self):
        job = create_job(
            self.snapshot,
            "index.html",
            [self.shas[0]],
        )

        claimed = claim_next_job()

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.pk, job.pk)
        self.assertEqual(claimed.status, Job.Status.PROCESSING)
        self.assertIsNotNone(claimed.started_at)

        # Verify the change was saved.
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PROCESSING)
        self.assertEqual(job.started_at, claimed.started_at)

        # Claiming the job hasn't started individual captures yet.
        self.assertEqual(
            job.captures[0].status,
            Capture.Status.PENDING,
        )

        # The claimed job is no longer available.
        self.assertIsNone(claim_next_job())

    def test_claim_chooses_oldest_queued_job(self):
        newer = create_job(
            self.snapshot,
            "index.html",
            [self.shas[0]],
        )

        older = create_job(
            self.snapshot,
            "about.html",
            [self.shas[1]],
        )

        # Make the second-created record older deliberately.
        Job.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=1),
        )

        self.assertEqual(claim_next_job().pk, older.pk)
        self.assertEqual(claim_next_job().pk, newer.pk)
        self.assertIsNone(claim_next_job())

    def test_claim_ignores_nonqueued_jobs(self):
        statuses = [
            Job.Status.PROCESSING,
            Job.Status.COMPLETE,
            Job.Status.PARTIALLY_COMPLETE,
            Job.Status.FAILED,
        ]

        for status in statuses:
            job = create_job(
                self.snapshot,
                "index.html",
                [self.shas[0]],
            )

            Job.objects.filter(pk=job.pk).update(status=status)

        self.assertIsNone(claim_next_job())