from .services.github import parse_github_url
from rest_framework import serializers

from .models import Project


class ProjectCreateSerializer(serializers.Serializer):
    project_name = serializers.CharField(max_length=200)
    repository_url = serializers.URLField(max_length=500)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = False

    def validate_repository_url(self, value):
        try:
            parse_github_url(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error)) from error

        return value

    def create(self, validated_data):
        project, self.created = Project.objects.get_or_create(
            repository_url=validated_data["repository_url"],
            defaults={"name": validated_data["project_name"]},
        )
        return project