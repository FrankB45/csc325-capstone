from rest_framework import serializers
from .models import Comparison

class CreateAnalysisSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=500)

    page_path = serializers.CharField(
        max_length=500,
        trim_whitespace=False,
    )

    commit_shas = serializers.ListField(
        child=serializers.RegexField(r"\A[0-9a-f]{40}\Z"),
        min_length=1,
        max_length=10,
    )

    name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    project_id = serializers.RegexField(r"\A[0-9a-fA-F]{24}\Z", required=False)
    source_job_id = serializers.RegexField(r"\A[0-9a-fA-F]{24}\Z", required=False)

    def validate(self, attrs):
        if "project_id" in attrs and "source_job_id" not in attrs:
            raise serializers.ValidationError({
                "source_job_id": "Include the saved analysis being updated.",
            })
        if "source_job_id" in attrs and "project_id" not in attrs:
            raise serializers.ValidationError({
                "project_id": "Include the existing project being updated.",
            })
        return attrs


class CreatePageAnalysisSerializer(serializers.Serializer):
    page_path = serializers.CharField(max_length=500, trim_whitespace=False)


class CreateComparisonSerializer(serializers.Serializer):
    first_position = serializers.IntegerField(min_value=0, max_value=9)
    second_position = serializers.IntegerField(min_value=0, max_value=9)

    def validate(self, attrs):
        if attrs["first_position"] == attrs["second_position"]:
            raise serializers.ValidationError(
                "Choose two different screenshots."
            )
        return attrs


class ComparisonSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    capture_job_id = serializers.CharField(read_only=True)

    class Meta:
        model = Comparison
        fields = (
            "id",
            "capture_job_id",
            "before_position",
            "after_position",
            "status",
            "result",
            "result_source",
            "model_name",
            "prompt_version",
            "error_code",
            "error_message",
            "llm_error",
            "attempts",
            "created_at",
            "started_at",
            "completed_at",
        )
        read_only_fields = fields
