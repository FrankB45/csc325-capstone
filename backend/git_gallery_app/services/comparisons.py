from pydantic import BaseModel, ConfigDict
from .llm import request_image_comparison


class ComparisonChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element: str | None
    location: str | None
    file_path: str | None
    description: str


class ComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: list[ComparisonChange]
    limitations: list[str]

def compare_screenshots(before_path, after_path):
    return request_image_comparison(
        before_path,
        after_path,
        result_type=ComparisonResult,
    )