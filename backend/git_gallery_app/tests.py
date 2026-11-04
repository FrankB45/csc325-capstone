from django.test import TestCase

from django.test import TransactionTestCase
from django.utils import timezone

from .models import Project, RepositorySnapshot, Commit, Job, Capture
from .services.jobs import create_job


class CreateJobTests(TransactionTestCase):
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