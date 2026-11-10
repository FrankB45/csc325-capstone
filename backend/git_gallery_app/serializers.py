from rest_framework import serializers


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

