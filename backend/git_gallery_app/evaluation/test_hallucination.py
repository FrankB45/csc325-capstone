"""Ground visual comparisons in screenshots and supported source patches."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError


TASK_ID = "compare_commits"
WORD_PATTERN = re.compile(r"[a-z0-9]+")


def parse_response(response: str) -> tuple[dict | None, list[str]]:
    try:
        parsed = json.loads(response)
    except (TypeError, json.JSONDecodeError):
        return None, ["response is not valid JSON"]
    if not isinstance(parsed, dict):
        return None, ["response must be a JSON object"]
    return parsed, []


def _normalize(text: str) -> str:
    return " ".join(WORD_PATTERN.findall(text.lower()))


def _flatten(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return ""


def _criterion_matches(text: str, criterion: dict) -> bool:
    text_tokens = set(_normalize(text).split())
    for phrase in criterion.get("phrases", []):
        normalized = _normalize(phrase)
        if normalized and f" {normalized} " in f" {_normalize(text)} ":
            return True
        phrase_tokens = set(normalized.split())
        if len(phrase_tokens) >= 3:
            overlap = len(phrase_tokens & text_tokens) / len(phrase_tokens)
            if overlap >= 0.7:
                return True
    return False


def _supported_file_paths(case: dict) -> set[str]:
    paths = set()
    for entry in case.get("repository_data", {}).get("source_context", []):
        if not isinstance(entry, dict):
            continue
        patch = entry.get("patch")
        path = entry.get("file_path")
        if (
            isinstance(path, str)
            and path
            and isinstance(patch, str)
            and patch.strip()
            and entry.get("patch_truncated") is not True
        ):
            paths.add(path)
    return paths


def response_failures(case: dict, response: dict) -> list[str]:
    from git_gallery_app.comparison_schema import ComparisonResult

    if case.get("task", {}).get("id") != TASK_ID:
        return ["unsupported analysis task; only compare_commits is in scope"]

    try:
        result = ComparisonResult.model_validate(response)
    except ValidationError as exc:
        failures = []
        for error in exc.errors(include_input=False, include_url=False):
            field = ".".join(map(str, error["loc"])) or "response"
            failures.append(f"{field}: {error['type']}")
        return failures

    # A reported visual change needs a meaningful description.
    return [
        f"change {index} must have a nonempty description"
        for index, change in enumerate(result.changes, start=1)
        if not change.description.strip()
    ]


def evaluate_hallucination(case: dict, response_text: str) -> list[str]:
    response, errors = parse_response(response_text)
    if errors:
        return errors
    failures = response_failures(case, response)
    if failures:
        return failures

    response_text_all = _flatten(response)
    for item in case.get("required_facts", []):
        if not _criterion_matches(response_text_all, item):
            failures.append(f"missing required fact: {item.get('fact', 'unspecified fact')}")
    for item in case.get("required_limitations", []):
        if not _criterion_matches(_flatten(response["limitations"]), item):
            failures.append(f"missing required limitation: {item.get('behavior', 'unspecified limitation')}")
    for item in case.get("forbidden_claims", []):
        if _criterion_matches(response_text_all, item):
            failures.append(f"contains forbidden claim: {item.get('claim', 'unspecified claim')}")

    before_observation = case["repository_data"].get("before_screenshot_observation")
    after_observation = case["repository_data"].get("after_screenshot_observation")
    if not before_observation or not after_observation:
        if response["changes"]:
            failures.append("a comparison with unavailable screenshot evidence must return no changes")

    supported_paths = _supported_file_paths(case)
    for index, change in enumerate(response["changes"]):
        file_path = change["file_path"]
        if file_path is not None and file_path not in supported_paths:
            failures.append(
                f"change {index + 1} uses unsupported or truncated file_path: {file_path}"
            )

    if not response["changes"] and not response["limitations"]:
        failures.append("empty changes must include evidence limitations or explain that no visible difference was identified")

    return failures


def semantic_signature(case: dict, response_text: str) -> tuple | None:
    response, errors = parse_response(response_text)
    if errors or response_failures(case, response):
        return None

    changes = tuple(sorted(
        (
            _normalize(change["element"]) if change["element"] is not None else "",
            _normalize(change["location"]) if change["location"] is not None else "",
            change["file_path"] or "",
            tuple(
                _criterion_matches(change["description"], item)
                for item in case.get("required_facts", [])
            ),
        )
        for change in response["changes"]
    ))
    limitations = tuple(sorted(_normalize(item) for item in response["limitations"]))
    fact_matches = tuple(
        _criterion_matches(_flatten(response), item)
        for item in case.get("required_facts", [])
    )
    limitation_matches = tuple(
        _criterion_matches(_flatten(response["limitations"]), item)
        for item in case.get("required_limitations", [])
    )
    forbidden_matches = tuple(
        _criterion_matches(_flatten(response), item)
        for item in case.get("forbidden_claims", [])
    )
    return changes, limitations, fact_matches, limitation_matches, forbidden_matches


def evaluate_hallucination_suite(cases: list[dict], responses: dict[str, str]) -> list[dict]:
    results = []
    for case in cases:
        failures = evaluate_hallucination(case, responses[case["id"]])
        results.append({"id": case["id"], "passed": not failures, "failures": failures})
    return results
