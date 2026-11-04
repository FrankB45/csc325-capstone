from rest_framework import serializers

from .models import Project


class ProjectCreateSerializer(serializers.Serializer):
    project_name = serializers.CharField(max_length=200)
    repository_owner = serializers.CharField(max_length=100)
    repository_name = serializers.CharField(max_length=100)
    repository_url = serializers.URLField(max_length=500)
    analysis_status = serializers.ChoiceField(
        choices=Project.AnalysisStatus.choices,
        default=Project.AnalysisStatus.NOT_STARTED,
    )
    processed_versions = serializers.IntegerField(min_value=0, default=0)
    total_versions = serializers.IntegerField(min_value=0, default=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = False

    def validate(self, attributes):
        if attributes["processed_versions"] > attributes["total_versions"]:
            raise serializers.ValidationError(
                "Processed versions cannot exceed the selected total."
            )
        return attributes

def create(self, validated_data):
    project, self.created = Project.objects.get_or_create(
        repository_url=validated_data["repository_url"],
        defaults={"name": validated_data["project_name"]},
    )
    return project


class ProjectStatusSerializer(serializers.Serializer):
    analysis_status = serializers.ChoiceField(
        choices=Project.AnalysisStatus.choices,
        required=False,
    )
    processed_versions = serializers.IntegerField(min_value=0, required=False)
    total_versions = serializers.IntegerField(min_value=0, required=False)

    def validate(self, attributes):
        project = self.context["project"]
        processed_versions = attributes.get(
            "processed_versions",
            project.processed_versions,
        )
        total_versions = attributes.get("total_versions", project.total_versions)

        if not attributes:
            raise serializers.ValidationError(
                "Provide an analysis status or version count to update."
            )
        if processed_versions > total_versions:
            raise serializers.ValidationError(
                "Processed versions cannot exceed the selected total."
            )
        return attributes

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class SavedAnalysisSerializer(serializers.Serializer):
    analysis_status = serializers.ChoiceField(
        choices=[
            (status, label)
            for status, label in Project.AnalysisStatus.choices
            if status != Project.AnalysisStatus.NOT_STARTED
        ],
    )
    processed_versions = serializers.IntegerField(min_value=0)
    total_versions = serializers.IntegerField(min_value=1)
    results = serializers.JSONField()

    def validate_results(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Results must be a JSON object.")
        return value

    def validate(self, attributes):
        if attributes["processed_versions"] > attributes["total_versions"]:
            raise serializers.ValidationError(
                "Processed versions cannot exceed the selected total."
            )
        return attributes
