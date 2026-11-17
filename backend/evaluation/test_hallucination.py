"""Ground repository analyses in their supplied commits and screenshots."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable


TASK_IDS = {
    "commit_summary",
    "group_commits",
    "recommend_captures",
    "visual_change_analysis",
}
SHA_PATTERN = re.compile(r"(?<![A-Za-z0-9])([0-9a-fA-F]{7,40})(?![A-Za-z0-9])")
FILE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_./-]+\."
    r"(?:html|css|js|jsx|ts|tsx|json|md|png|jpg|jpeg|svg))\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z)?\b")
AUTHOR_PATTERN = re.compile(
    r"\b(?:author(?:ed)? by|author is|author:|written by|committed by)\s+"
    r"([A-Z][A-Za-z'-]+)\b",
    re.IGNORECASE,
)


def parse_response(response: str) -> tuple[dict | None, list[str]]:
    try:
        parsed = json.loads(response)
    except (TypeError, json.JSONDecodeError):
        return None, ["response is not valid JSON"]
    if not isinstance(parsed, dict):
        return None, ["response must be a JSON object"]
    return parsed, []


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = f" {_normalize(text)} "
    normalized_phrase = _normalize(phrase)
    return bool(normalized_phrase) and f" {normalized_phrase} " in normalized_text


def _flatten(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return ""


def _shape_failures(case: dict, response: dict) -> list[str]:
    task_id = case.get("task", {}).get("id")
    expected = case.get("expected_output", {})
    if task_id not in TASK_IDS:
        return [f"unsupported analysis task: {task_id}"]
    if not isinstance(expected, dict) or response.keys() != expected.keys():
        return ["response fields do not match the selected task's expected output format"]

    if task_id == "commit_summary":
        if not (
            isinstance(response.get("commit_sha"), str)
            and isinstance(response.get("files_changed"), list)
            and all(isinstance(item, str) for item in response["files_changed"])
            and isinstance(response.get("summary"), str)
            and isinstance(response.get("major_changes"), list)
            and all(isinstance(item, str) for item in response["major_changes"])
            and isinstance(response.get("limitations"), list)
            and all(isinstance(item, str) for item in response["limitations"])
        ):
            return ["commit summary has invalid field types"]
    elif task_id == "group_commits":
        groups = response.get("groups")
        if not isinstance(groups, list) or not isinstance(response.get("limitations"), list):
            return ["commit grouping must contain groups and limitations lists"]
        for index, group in enumerate(groups):
            if (
                not isinstance(group, dict)
                or group.keys() != {"commit_shas", "title", "rationale"}
                or not isinstance(group["commit_shas"], list)
                or not all(isinstance(item, str) for item in group["commit_shas"])
                or not isinstance(group["title"], str)
                or not isinstance(group["rationale"], str)
            ):
                return [f"group {index + 1} has an invalid structure"]
    elif task_id == "recommend_captures":
        if not (
            isinstance(response.get("recommended_commit_shas"), list)
            and all(isinstance(item, str) for item in response["recommended_commit_shas"])
            and isinstance(response.get("rationale"), str)
            and isinstance(response.get("limitations"), list)
        ):
            return ["capture recommendations have invalid field types"]
    else:
        changes = response.get("changes")
        if not isinstance(changes, list) or not isinstance(response.get("limitations"), list):
            return ["visual comparison must contain changes and limitations lists"]
        for index, change in enumerate(changes):
            if (
                not isinstance(change, dict)
                or change.keys() != {"element", "before", "after", "evidence"}
                or not all(isinstance(value, str) for value in change.values())
            ):
                return [f"visual change {index + 1} has an invalid structure"]
    return []


def _known_commits(case: dict) -> set[str]:
    repository_data = case.get("repository_data", {})
    commits = repository_data.get("commits", [])
    identifiers = {
        commit["sha"].lower()
        for commit in commits
        if isinstance(commit, dict) and isinstance(commit.get("sha"), str)
    }
    for key in ("before", "after"):
        snapshot = repository_data.get(key)
        if isinstance(snapshot, dict) and isinstance(snapshot.get("commit_sha"), str):
            identifiers.add(snapshot["commit_sha"].lower())
    return identifiers


def _known_repository_values(case: dict) -> tuple[set[str], set[str], set[str]]:
    repository_data = case.get("repository_data", {})
    files = set()
    authors = set()
    timestamps = set()
    for commit in repository_data.get("commits", []):
        if not isinstance(commit, dict):
            continue
        files.update(path.lower() for path in commit.get("changed_files", []))
        if isinstance(commit.get("author"), str):
            authors.add(commit["author"].lower())
        if isinstance(commit.get("timestamp"), str):
            timestamps.add(commit["timestamp"])
            timestamps.add(commit["timestamp"][:10])
    return files, authors, timestamps


def _reference_failures(case: dict, response: dict) -> list[str]:
    task_id = case["task"]["id"]
    known_commits = _known_commits(case)
    known_files, known_authors, known_timestamps = _known_repository_values(case)
    output_text = _flatten(response)
    failures = []

    for identifier in SHA_PATTERN.findall(output_text):
        if identifier.lower() not in known_commits:
            failures.append(f"invented or unsupported commit identifier: {identifier}")
    for path in FILE_PATTERN.findall(output_text):
        if path.lower() not in known_files:
            failures.append(f"references a file outside the supplied repository data: {path}")
    for author in AUTHOR_PATTERN.findall(output_text):
        if author.lower() not in known_authors:
            failures.append(f"references an unsupported commit author: {author}")
    for timestamp in DATE_PATTERN.findall(output_text):
        if timestamp not in known_timestamps:
            failures.append(f"references an unsupported timestamp: {timestamp}")

    if task_id == "commit_summary":
        target_sha = case["repository_data"].get("target_commit_sha")
        target = next(
            (commit for commit in case["repository_data"].get("commits", [])
             if commit.get("sha") == target_sha),
            None,
        )
        if target is None:
            failures.append("target commit is not present in the supplied repository data")
        else:
            if response["commit_sha"].lower() != target_sha.lower():
                failures.append("summary refers to a different commit than the selected target")
            expected_files = set(target.get("changed_files", []))
            actual_files = set(response["files_changed"])
            if actual_files != expected_files:
                fabricated = actual_files - expected_files
                missing = expected_files - actual_files
                if fabricated:
                    failures.append(f"claims unsupported changed files: {', '.join(sorted(fabricated))}")
                if missing:
                    failures.append(f"omits changed files: {', '.join(sorted(missing))}")

    elif task_id == "group_commits":
        actual_groups = [group["commit_shas"] for group in response["groups"]]
        flattened = [sha for group in actual_groups for sha in group]
        expected_history = [commit["sha"] for commit in case["repository_data"].get("commits", [])]
        if len(flattened) != len(set(flattened)):
            failures.append("grouping assigns a commit more than once")
        if set(flattened) != set(expected_history):
            failures.append("grouping omits commits or includes commits outside the supplied history")
        positions = {sha: index for index, sha in enumerate(expected_history)}
        for group in actual_groups:
            indexes = [positions[sha] for sha in group if sha in positions]
            if indexes and indexes != list(range(min(indexes), max(indexes) + 1)):
                failures.append("a group combines non-consecutive commits")
                break
        if "expected_groups" in case:
            expected_groups = {
                frozenset(group) for group in case["expected_groups"]
            }
            if {frozenset(group) for group in actual_groups} != expected_groups:
                failures.append("group membership does not match the evidence-based reference")

    elif task_id == "recommend_captures":
        recommendations = response["recommended_commit_shas"]
        if len(recommendations) != len(set(recommendations)):
            failures.append("capture recommendations contain duplicate commits")
        unknown = set(recommendations) - known_commits
        if unknown:
            failures.append(f"recommends commits outside the supplied history: {', '.join(sorted(unknown))}")
        if "expected_commit_ids" in case and set(recommendations) != set(case["expected_commit_ids"]):
            failures.append("recommended commits do not match the reference")
    return failures


def _criterion_matches(text: str, criterion: dict) -> bool:
    return any(_contains_phrase(text, phrase) for phrase in criterion.get("phrases", []))


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
    """Check task-specific structure, known repository facts, and prohibited claims."""
    response, errors = parse_response(response_text)
    if errors:
        return errors

    failures = _shape_failures(case, response)
    if failures:
        return failures

    failures.extend(_reference_failures(case, response))
    flattened_response = _flatten(response)
    failures.extend(_check_criteria(flattened_response, case.get("required_facts", []), "fact"))
    failures.extend(
        _check_criteria(flattened_response, case.get("required_behaviors", []), "behavior")
    )
    failures.extend(
        _check_criteria(
            _flatten(response.get("limitations", [])),
            case.get("required_limitations", []),
            "limitation",
        )
    )
    for item in case.get("forbidden_claims", []):
        if _criterion_matches(flattened_response, item):
            failures.append(f"contains forbidden claim: {item.get('claim', 'unspecified claim')}")
    return failures


def semantic_signature(case: dict, response_text: str) -> tuple | None:
    """Build a wording-tolerant signature for the selected analysis task."""
    response, errors = parse_response(response_text)
    if errors or _shape_failures(case, response):
        return None

    task_id = case["task"]["id"]
    fact_matches = tuple(
        _criterion_matches(_flatten(response), item)
        for item in case.get("required_facts", [])
    )
    behavior_matches = tuple(
        _criterion_matches(_flatten(response), item)
        for item in case.get("required_behaviors", [])
    )
    forbidden_matches = tuple(
        _criterion_matches(_flatten(response), item)
        for item in case.get("forbidden_claims", [])
    )
    limitation_matches = tuple(
        _criterion_matches(_flatten(response.get("limitations", [])), item)
        for item in case.get("required_limitations", [])
    )

    if task_id == "commit_summary":
        task_signature = (
            response["commit_sha"].lower(),
            tuple(sorted(response["files_changed"])),
            len(response["major_changes"]),
        )
    elif task_id == "group_commits":
        task_signature = tuple(sorted(
            (
                tuple(sorted(set(group["commit_shas"]))),
                tuple(
                    _criterion_matches(group["rationale"], item)
                    for item in case.get("required_facts", [])
                ),
            )
            for group in response["groups"]
        ))
    elif task_id == "recommend_captures":
        task_signature = tuple(sorted(set(response["recommended_commit_shas"])))
    else:
        task_signature = len(response["changes"])

    return (
        task_id,
        task_signature,
        len(response.get("limitations", [])),
        fact_matches,
        behavior_matches,
        forbidden_matches,
        limitation_matches,
    )


def evaluate_hallucination_suite(cases: list[dict], responses: dict[str, str]) -> list[dict]:
    results = []
    for case in cases:
        failures = evaluate_hallucination(case, responses[case["id"]])
        results.append({"id": case["id"], "passed": not failures, "failures": failures})
    return results
