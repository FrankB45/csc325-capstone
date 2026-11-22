"""Case format for the AI Compare evaluation.

Each case is one folder inside ``dataset/``:

    dataset/<case-id>/
        before.png    screenshot of the older commit
        after.png     screenshot of the newer commit
        diff.json     the exact dict get_diff_context() would return
        rubric.json   what a correct comparison must / must not contain

The inputs (PNGs + diff.json) are what production sends to the model.
The rubric is the answer key. Keeping them in separate files makes it
obvious which is which.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from git_gallery_app.comparison_schema import ComparisonResult

DATASET_DIR = Path(__file__).resolve().parent / "dataset"

# Sprint requirement: the golden set must contain at least this many cases.
MIN_GOLDEN_CASES = 15

# Sentinel for ExpectedChange.expected_file_path: "don't grade the file".
ANY_FILE = "*"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SHA_PATTERN = r"^[0-9a-f]{40}$"
ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class CaseFormatError(ValueError):
    """A case folder is missing a file or contains invalid data."""


# ---------------------------------------------------------------------------
# diff.json: mirrors services/diff_context.get_diff_context() exactly
# ---------------------------------------------------------------------------

class DiffFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(min_length=1)
    previous_file_path: str | None
    status: str = Field(min_length=1)
    patch: str | None
    patch_truncated: bool


class DiffContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_path: str = Field(min_length=1)
    before_sha: str = Field(pattern=SHA_PATTERN)
    after_sha: str = Field(pattern=SHA_PATTERN)
    files: list[DiffFile]
    limitations: list[str]

    @model_validator(mode="after")
    def _distinct_commits(self):
        if self.before_sha == self.after_sha:
            raise ValueError("before_sha and after_sha must differ")
        return self

    def supported_paths(self) -> set[str]:
        """Files the model may cite: same rule as finalize_result()."""
        return {item.file_path for item in self.files if item.patch}

    def as_context(self) -> dict:
        """The plain dict production passes around (and json.dumps)."""
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# rubric.json: the answer key
# ---------------------------------------------------------------------------

class ExpectedChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    element: str = Field(min_length=1)
    before: str = Field(min_length=1)
    after: str = Field(min_length=1)
    # "*" = not graded, null = must be null, "path" = must equal this path
    expected_file_path: str | None = ANY_FILE
    # False = finding it is a bonus; reporting it never counts as invented
    required: bool = True


class Rubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    description: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    expect_no_changes: bool = False
    expected_changes: list[ExpectedChange] = Field(default_factory=list)
    allowed_extra_changes: int = Field(default=0, ge=0)
    forbidden_claims: list[str] = Field(default_factory=list)
    required_limitations: list[str] = Field(default_factory=list)
    # A hand-written ideal answer in the exact production response format.
    # Used to prove the graders score a perfect answer as perfect.
    reference_output: ComparisonResult
    # Cases sharing a bias_pair name are counterfactual twins: the same visual
    # change, differing only in something irrelevant (names, language, ...).
    bias_pair: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _consistent(self):
        if self.expect_no_changes:
            if self.expected_changes:
                raise ValueError("expect_no_changes cases cannot list expected_changes")
            if self.allowed_extra_changes:
                raise ValueError("expect_no_changes cases cannot allow extra changes")
            if self.reference_output.changes:
                raise ValueError("expect_no_changes cases need an empty reference_output.changes")
        elif not self.reference_output.changes:
            raise ValueError("reference_output.changes cannot be empty for a case with changes")
        elif not any(change.required for change in self.expected_changes):
            raise ValueError(
                "list at least one required expected change, "
                "or set expect_no_changes to true"
            )

        ids = [change.id for change in self.expected_changes]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate expected change ids: {duplicates}")
        return self


# ---------------------------------------------------------------------------
# A loaded case
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Case:
    id: str
    directory: Path
    before_png: Path
    after_png: Path
    diff: DiffContext
    rubric: Rubric

    @property
    def tags(self) -> list[str]:
        return self.rubric.tags


def _read_model(path: Path, model: type[BaseModel]):
    if not path.is_file():
        raise CaseFormatError(f"{path.parent.name}: missing {path.name}")
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(map(str, e['loc'])) or '(root)'}: {e['msg']}"
            for e in error.errors(include_url=False)
        )
        raise CaseFormatError(f"{path.parent.name}/{path.name}: {problems}") from error


def _check_png(path: Path) -> Path:
    if not path.is_file():
        raise CaseFormatError(f"{path.parent.name}: missing {path.name}")
    with path.open("rb") as handle:
        if handle.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
            raise CaseFormatError(f"{path.parent.name}/{path.name} is not a PNG file")
    return path


def load_case(directory: Path) -> Case:
    directory = Path(directory)
    diff = _read_model(directory / "diff.json", DiffContext)
    rubric = _read_model(directory / "rubric.json", Rubric)

    if rubric.id != directory.name:
        raise CaseFormatError(
            f"{directory.name}: rubric id {rubric.id!r} must match the folder name"
        )

    supported = diff.supported_paths()
    for change in rubric.expected_changes:
        path = change.expected_file_path
        if path not in (ANY_FILE, None) and path not in supported:
            raise CaseFormatError(
                f"{directory.name}: expected change {change.id!r} expects "
                f"file {path!r}, but diff.json has no patch for it"
            )
    
    reference = rubric.reference_output
    for index, change in enumerate(reference.changes, start=1):
        if change.file_path is not None and change.file_path not in supported:
            raise CaseFormatError(
                f"{directory.name}: reference_output change {index} cites "
                f"{change.file_path!r}, but diff.json has no patch for it"
            )

    repeated = sorted(set(reference.limitations) & set(diff.limitations))
    if repeated:
        raise CaseFormatError(
            f"{directory.name}: reference_output repeats limitations the app "
            f"already adds: {repeated}"
        )

    return Case(
        id=rubric.id,
        directory=directory,
        before_png=_check_png(directory / "before.png"),
        after_png=_check_png(directory / "after.png"),
        diff=diff,
        rubric=rubric,
    )


def load_dataset(
    root: Path = DATASET_DIR,
    *,
    ids: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[Case]:
    """Load every case folder under root, optionally filtered by id or tag."""
    root = Path(root)
    if not root.is_dir():
        raise CaseFormatError(f"dataset folder not found: {root}")

    cases = [
        load_case(folder)
        for folder in sorted(root.iterdir())
        if folder.is_dir() and not folder.name.startswith((".", "_"))
    ]
    
    bias_pairs(cases)  # validate pairs across the whole dataset
    
    if ids:
        known = {case.id for case in cases}
        unknown = sorted(set(ids) - known)
        if unknown:
            raise CaseFormatError(f"unknown case ids: {unknown}")
        cases = [case for case in cases if case.id in ids]

    if tags:
        cases = [case for case in cases if set(tags) & set(case.tags)]

    if not cases:
        raise CaseFormatError("no cases matched")
    return cases

def bias_pairs(cases: list[Case]) -> dict[str, tuple[Case, Case]]:
    """Group counterfactual twins by bias_pair name, checking each pair is valid."""
    groups: dict[str, list[Case]] = {}
    for case in cases:
        if case.rubric.bias_pair:
            groups.setdefault(case.rubric.bias_pair, []).append(case)

    pairs = {}
    for name, members in sorted(groups.items()):
        if len(members) != 2:
            raise CaseFormatError(
                f"bias pair {name!r} needs exactly 2 cases, found {len(members)}"
            )
        first, second = members
        first_ids = [change.id for change in first.rubric.expected_changes]
        second_ids = [change.id for change in second.rubric.expected_changes]
        if first_ids != second_ids:
            raise CaseFormatError(
                f"bias pair {name!r}: {first.id} and {second.id} must list "
                f"the same expected change ids"
            )
        pairs[name] = (first, second)
    return pairs