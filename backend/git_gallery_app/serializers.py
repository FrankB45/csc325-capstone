from rest_framework import serializers

from .models import Project


class ProjectCreateSerializer(serializers.Serializer):
    project_name = serializers.CharField(max_length=200)
    repository_url = serializers.URLField(max_length=500)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = False

    def create(self, validated_data):
        project, self.created = Project.objects.get_or_create(
            repository_url=validated_data["repository_url"],
            defaults={"name": validated_data["project_name"]},
        )
        return project