from django.db import models
from django_mongodb_backend.fields import (
    EmbeddedModelArrayField,
    ArrayField,
    )
from django_mongodb_backend.models import EmbeddedModel

class Project(models.Model):
    name = models.CharField(max_length=200)
    repository_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects"
    def __str__(self):
        return self.name


class Capture(EmbeddedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"
    
    commit_sha = models.CharField(max_length=40)
    position = models.PositiveSmallIntegerField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    screenshot_path = models.CharField(
        max_length=500,
        default="",
        blank=True
    )

    completed_at = models.DateTimeField(null=True, blank=True)

    error_message = models.TextField(default="", blank=True)

    def __str__(self):
        return f"{self.commit_sha[:7]} — {self.status}"


class Commit(EmbeddedModel):
    sha = models.CharField(max_length=40)
    message = models.TextField(default="", blank=True)
    author_name = models.CharField(max_length=255)
    committed_at = models.DateTimeField()
    position = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.sha[:7]} — {self.message.splitlines()[0] if self.message else ''}"

class RepositorySnapshot(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="repository_snapshots"
    )

    repository_url = models.URLField(max_length=500)
    default_branch = models.CharField(max_length=255)
    head_sha = models.CharField(max_length=40)

    commits = EmbeddedModelArrayField(
        Commit,
        max_size = 50,
        default = list,
    )

    available_pages = ArrayField(
        models.CharField(max_length=500),
        default=list,
    )

    default_page = models.CharField(
        max_length=500,
        default="",
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "repository_snapshots"

    def __str__(self):
        return f"{self.repository_url} @ {self.head_sha[:7]}"


class Job(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETE = "complete", "Complete"
        PARTIALLY_COMPLETE = "partially_complete", "Partially Complete"
        FAILED = "failed", "Failed"

        
    repo_snapshot = models.ForeignKey(
        RepositorySnapshot,
        on_delete=models.CASCADE,
        related_name="jobs",
    )

    page_path = models.CharField(max_length=500)

    viewport_width = models.PositiveIntegerField(default=1440)
    viewport_height = models.PositiveIntegerField(default=900)

    full_page = models.BooleanField(default=True)

    captures = EmbeddedModelArrayField(
        Capture,
        max_size = 10,
        default = list,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    error_message = models.TextField(default="", blank=True)

    class Meta:
        db_table = "jobs"
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

