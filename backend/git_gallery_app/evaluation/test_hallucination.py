"""Ground two-commit visual comparisons in their supplied screenshot evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable


TASK_ID = "compare_commits"
SHA_PATTERN = re.compile(r"(?<![A-Za-z0-9])([0-9a-fA-F]{7,40})(?![A-Za-z0-9])")
WORD_PATTERN = re.compile(r"[a-z0-9]+")
NEGATION_PATTERN = re.compile(r"\b(?:no|not|never|cannot|can't|without|doesn't|don't)\b", re.I)


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


def _text_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _text_values(item)]
    if isinstance(value, list):
        return [text for item in value for text in _text_values(item)]
    return []


def _shape_failures(case: dict, response: dict) -> list[str]:
    if case.get("task", {}).get("id") != TASK_ID:
        return ["unsupported analysis task; only compare_commits is in scope"]
    expected = case.get("expected_output")
    required_keys = {
        "before_commit_sha",
        "after_commit_sha",
        "changes",
        "limitations",
    }
    if not isinstance(expected, dict) or set(expected) != required_keys:
        return ["golden expected_output does not match the compare_commits format"]
    if set(response) != required_keys:
        return ["response fields do not match the compare_commits output format"]
    if not (
        isinstance(response["before_commit_sha"], str)
        and isinstance(response["after_commit_sha"], str)
        and isinstance(response["changes"], list)
        and isinstance(response["limitations"], list)
        and all(isinstance(item, str) for item in response["limitations"])
    ):
        return ["comparison response has invalid field types"]
    for index, change in enumerate(response["changes"]):
        if (
            not isinstance(change, dict)
            or set(change) != {"element", "before", "after", "evidence"}
            or not all(isinstance(value, str) for value in change.values())
        ):
            return [f"change {index + 1} must include string element, before, after, and evidence fields"]
    return []


def _criterion_matches(text: str, criterion: dict) -> bool:
    text_tokens = _normalize(text).split()
    text_token_set = set(text_tokens)
    for phrase in criterion.get("phrases", []):
        phrase_tokens = _normalize(phrase).split()
        if not phrase_tokens:
            continue
        if f" {' '.join(phrase_tokens)} " in f" {' '.join(text_tokens)} ":
            return True
        phrase_token_set = set(phrase_tokens)
        if len(phrase_token_set) < 3:
            continue
        overlap = len(phrase_token_set & text_token_set) / len(phrase_token_set)
        if overlap >= 0.7:
            return True
    return False


def _check_criteria(
    response_text: str,
    criteria: Iterable[dict],
    label: str,
) -> list[str]:
    failures = []
    for item in criteria:
        if not _criterion_matches(response_text, item):
            description = item.get("fact") or item.get("behavior") or "unspecified requirement"
            failures.append(f"missing required {label}: {description}")
    return failures


def evaluate_hallucination(case: dict, response_text: str) -> list[str]:
    """Validate the selected pair, structured changes, evidence, and limitations."""
    response, errors = parse_response(response_text)
    if errors:
        return errors
    failures = _shape_failures(case, response)
    if failures:
        return failures

    before = case.get("repository_data", {}).get("before", {})
    after = case.get("repository_data", {}).get("after", {})
    before_sha = before.get("sha")
    after_sha = after.get("sha")
    if not isinstance(before_sha, str) or not isinstance(after_sha, str):
        failures.append("golden case must provide two commit identifiers")
        return failures

    if response["before_commit_sha"].lower() != before_sha.lower():
        failures.append("response does not identify the selected before commit")
    if response["after_commit_sha"].lower() != after_sha.lower():
        failures.append("response does not identify the selected after commit")

    expected_changes = case["expected_output"]["changes"]
    expected_states = sorted(
        (_normalize(change["before"]), _normalize(change["after"]))
        for change in expected_changes
    )
    actual_states = sorted(
        (_normalize(change["before"]), _normalize(change["after"]))
        for change in response["changes"]
    )
    if actual_states != expected_states:
        failures.append("reported before/after states do not match the reference comparison")

    known_shas = {before_sha.lower(), after_sha.lower()}
    for sha in SHA_PATTERN.findall(_flatten(response)):
        if sha.lower() not in known_shas:
            failures.append(f"response includes an unsupported commit identifier: {sha}")

    response_text_all = _flatten(response)
    failures.extend(_check_criteria(response_text_all, case.get("required_facts", []), "fact"))
    failures.extend(
        _check_criteria(response_text_all, case.get("required_behaviors", []), "behavior")
    )
    failures.extend(
        _check_criteria(
            _flatten(response["limitations"]),
            case.get("required_limitations", []),
            "limitation",
        )
    )
    for item in case.get("forbidden_claims", []):
        claim_present = any(
            _criterion_matches(text, item) and not NEGATION_PATTERN.search(text)
            for text in _text_values(response)
        )
        if claim_present:
            failures.append(f"contains forbidden claim: {item.get('claim', 'unspecified claim')}")

    if not response["changes"] and not response["limitations"]:
        failures.append("empty change list must state that no difference was identified or evidence is insufficient")
    return failures


def semantic_signature(case: dict, response_text: str) -> tuple | None:
    """Compare normalized structured changes and required factual signals."""
    response, errors = parse_response(response_text)
    if errors or _shape_failures(case, response):
        return None

    changes = tuple(sorted(
        (
            _normalize(change["before"]),
            _normalize(change["after"]),
            tuple(
                _criterion_matches(_flatten(change), item)
                for item in case.get("required_facts", [])
            ),
        )
        for change in response["changes"]
    ))
    facts = tuple(
        _criterion_matches(_flatten(response), item)
        for item in case.get("required_facts", [])
    )
    behaviors = tuple(
        _criterion_matches(_flatten(response), item)
        for item in case.get("required_behaviors", [])
    )
    limitation_count = len(response["limitations"])
    required_limitations = tuple(
        _criterion_matches(_flatten(response["limitations"]), item)
        for item in case.get("required_limitations", [])
    )
    return (
        response["before_commit_sha"].lower(),
        response["after_commit_sha"].lower(),
        changes,
        facts,
        behaviors,
        limitation_count,
        required_limitations,
    )


def evaluate_hallucination_suite(cases: list[dict], responses: dict[str, str]) -> list[dict]:
    results = []
    for case in cases:
        failures = evaluate_hallucination(case, responses[case["id"]])
        results.append({"id": case["id"], "passed": not failures, "failures": failures})
    return results
