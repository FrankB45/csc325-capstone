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


def evaluate(cases):
    results = []
    for case in cases:
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
