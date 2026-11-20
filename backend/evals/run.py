"""Offline contract evaluation for mocked AI commit recommendations."""

import json
from pathlib import Path

from git_gallery_app.commit_selection import SelectionError, validate_selection

MINIMUM_PASS_RATE = 1.0
CASES_PATH = Path(__file__).with_name("test_cases.json")


def response_is_valid(response, history):
    if not isinstance(response, dict):
        return False

    try:
        validate_selection(response.get("selected_commits"), history)
    except (SelectionError, TypeError):
        return False
    return True


def comparison_result_is_valid(response):
    if not isinstance(response, dict):
        return False

    changes = response.get("changes")
    limitations = response.get("limitations")
    if not isinstance(changes, list) or not isinstance(limitations, list):
        return False

    required_change_fields = ("element", "location", "file_path", "description")
    return all(
        isinstance(change, dict)
        and all(isinstance(change.get(field), str) for field in required_change_fields)
        for change in changes
    ) and all(isinstance(limitation, str) for limitation in limitations)


def commit_grouping_is_valid(response, history, commit_details):
    if (
        not isinstance(response, dict)
        or not isinstance(history, list)
        or any(not isinstance(commit, str) for commit in history)
    ):
        return False

    groups = response.get("groups")
    if not isinstance(groups, list) or not groups or len(set(history)) != len(history):
        return False

    history_indices = {commit: index for index, commit in enumerate(history)}
    grouped_commits = []
    previous_group_end = -1

    for group in groups:
        if not isinstance(group, dict):
            return False
        title = group.get("title")
        explanation = group.get("explanation")
        commits = group.get("commits")
        is_ui_milestone = group.get("likely_ui_milestone")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(explanation, str)
            or not explanation.strip()
            or not isinstance(commits, list)
            or not commits
            or any(not isinstance(commit, str) for commit in commits)
            or not isinstance(is_ui_milestone, bool)
        ):
            return False
        if any(commit not in history_indices for commit in commits):
            return False

        indices = [history_indices[commit] for commit in commits]
        if (
            indices != list(range(indices[0], indices[0] + len(indices)))
            or indices[0] <= previous_group_end
        ):
            return False
        previous_group_end = indices[-1]
        grouped_commits.extend(commits)

        if is_ui_milestone:
            if not isinstance(commit_details, dict):
                return False
            evidence = []
            for commit in commits:
                details = commit_details.get(commit)
                if not isinstance(details, dict):
                    continue
                message = details.get("message")
                files = details.get("changed_website_files")
                if isinstance(message, str) and message:
                    evidence.append(message)
                if isinstance(files, list):
                    evidence.extend(file for file in files if isinstance(file, str) and file)
            explanation_lower = explanation.casefold()
            if not any(item.casefold() in explanation_lower for item in evidence):
                return False
            if "screenshot" not in explanation_lower:
                return False

    return grouped_commits == history


def evaluate(cases):
    results = []
    for case in cases:
        if case.get("contract") == "comparison_result":
            actual = comparison_result_is_valid(case["mock_ai_response"])
        elif case.get("contract") == "commit_grouping":
            actual = commit_grouping_is_valid(
                case["mock_ai_response"], case["history"], case.get("commit_details")
            )
        else:
            actual = response_is_valid(case["mock_ai_response"], case["history"])
        results.append((case["name"], actual == case["expected_valid"]))
    return results


def main():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results = evaluate(cases)
    passed = sum(ok for _, ok in results)
    pass_rate = passed / len(results) if results else 0

    print(f"Mock AI contract evaluation: {passed}/{len(results)} ({pass_rate:.0%})")
    print(f"Required threshold: {MINIMUM_PASS_RATE:.0%}")
    for name, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}: {name}")

    return 0 if pass_rate >= MINIMUM_PASS_RATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
