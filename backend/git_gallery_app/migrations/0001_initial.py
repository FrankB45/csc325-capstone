import django_mongodb_backend.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    django_mongodb_backend.fields.ObjectIdAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("project_name", models.CharField(max_length=200)),
                ("repository_owner", models.CharField(max_length=100)),
                ("repository_name", models.CharField(max_length=100)),
                ("repository_url", models.URLField(max_length=500)),
                (
                    "analysis_status",
                    models.CharField(
                        choices=[
                            ("not_started", "Not Started"),
                            ("processing", "Processing"),
                            ("complete", "Complete"),
                            ("partially_complete", "Partially Complete"),
                            ("failed", "Failed"),
                        ],
                        default="not_started",
                        max_length=24,
                    ),
                ),
                ("processed_versions", models.PositiveIntegerField(default=0)),
                ("total_versions", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at", "project_name"]},
        ),
    ]
