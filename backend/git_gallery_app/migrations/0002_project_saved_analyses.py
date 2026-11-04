from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("git_gallery_app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="saved_analyses",
            field=models.JSONField(default=list),
        ),
    ]
