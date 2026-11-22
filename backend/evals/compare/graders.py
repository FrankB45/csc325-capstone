"""Deterministic (no-LLM) checks on one model answer for one case.

These are the checks that plain code can decide with certainty. Anything
that needs to understand meaning ("did it describe the header change?")
is left to the LLM judge in judge.py.

Every check belongs to one category:

    FORMAT         did the model return a usable answer at all?
    HALLUCINATION  did it add anything that shouldn't be there?
    ACCURACY       is anything that should be there missing?
"""

from __future__ import annotations

from dataclasses import dataclass

from git_gallery_app.comparison_schema import ComparisonResult

from .cases import Case

FORMAT = "format"
HALLUCINATION = "hallucination"
ACCURACY = "accuracy"


@dataclass(frozen=True)
class RunOutput:
    """One model call for one case: a parsed answer, or the error it raised."""

    raw: ComparisonResult | None
    error_code: str | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    category: str
    passed: bool
    detail: str = ""


def _check(name: str, category: str, passed: bool, failure_detail: str) -> CheckResult:
    return CheckResult(name, category, passed, "" if passed else failure_detail)


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, ignore a trailing period."""
    return " ".join(text.lower().split()).rstrip(".")


def run_hard_checks(case: Case, output: RunOutput) -> list[CheckResult]:
    if output.raw is None:
        return [_check(
            "valid_response", FORMAT, False,
            f"model call failed: {output.error_code or 'unknown error'}",
        )]

    raw = output.raw
    results = [_check("valid_response", FORMAT, True, "")]

    if case.rubric.expect_no_changes:
        results.append(_check(
            "empty_when_no_change", HALLUCINATION, not raw.changes,
            f"reported {len(raw.changes)} change(s) on a page with no visible change",
        ))
    else:
        results.append(_check(
            "reports_changes", ACCURACY, bool(raw.changes),
            "returned no changes, but the rubric expects at least one",
        ))

    supported = case.diff.supported_paths()
    unsupported = sorted({
        change.file_path
        for change in raw.changes
        if change.file_path is not None and change.file_path not in supported
    })
    results.append(_check(
        "file_paths_grounded", HALLUCINATION, not unsupported,
        f"cites files with no supplied patch: {unsupported}",
    ))

    app_notes = {_normalize(note) for note in case.diff.limitations}
    repeated = [note for note in raw.limitations if _normalize(note) in app_notes]
    results.append(_check(
        "no_repeated_app_limitations", HALLUCINATION, not repeated,
        f"repeats limitations the app already adds: {repeated}",
    ))

    return results


def passed(results: list[CheckResult], *categories: str) -> bool:
    """True if every check in the given categories passed (all if none given)."""
    return all(
        result.passed
        for result in results
        if not categories or result.category in categories
    )


def failures(results: list[CheckResult]) -> list[CheckResult]:
    return [result for result in results if not result.passed]