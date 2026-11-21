from pydantic import BaseModel, ConfigDict


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