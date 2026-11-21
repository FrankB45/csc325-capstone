"""Run reference-grounded and repeated-run evaluation checks."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from llm_adapter import build_adapter
from test_consistency import evaluate_consistency_suite
from test_hallucination import (
    TASK_ID,
    _shape_failures,
    evaluate_hallucination_suite,
)


HERE = Path(__file__).resolve().parent
GOLDEN_SET_PATH = HERE / "golden_set.json"
SYSTEM_PROMPT_PATH = HERE.parent / "prompts" / "system_prompt.txt"
HALLUCINATION_THRESHOLD = 0.90
CONSISTENCY_THRESHOLD = 0.80


def load_golden_set(path: Path = GOLDEN_SET_PATH) -> list[dict]:
    try:
        cases = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load golden dataset at {path}: {error}") from error

    if not isinstance(cases, list) or len(cases) < 15:
        raise ValueError("Golden dataset must be a list with at least 15 cases.")

    ids = set()
    required_keys = {
        "id",
        "category",
        "task",
        "repository_data",
        "expected_output",
        "forbidden_claims",
    }
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or not required_keys.issubset(case):
            raise ValueError(f"Golden case {index + 1} is missing required fields.")
        if not all(isinstance(case[key], str) and case[key].strip()
                   for key in ("id", "category")):
            raise ValueError(f"Golden case {index + 1} has an empty or invalid text field.")
        if case["id"] in ids:
            raise ValueError(f"Duplicate golden case id: {case['id']}")
        ids.add(case["id"])
        if (
            not isinstance(case["task"], dict)
            or case["task"].get("id") != TASK_ID
            or not isinstance(case["task"].get("question"), str)
            or not case["task"]["question"].strip()
        ):
            raise ValueError(f"Golden case {case['id']} must select the compare_commits task.")
        if not isinstance(case["repository_data"], dict):
            raise ValueError(f"Golden case {case['id']} needs repository_data.")
        before_sha = case["repository_data"].get("before_commit_sha")
        after_sha = case["repository_data"].get("after_commit_sha")
        if (
            not isinstance(before_sha, str)
            or not isinstance(after_sha, str)
            or not before_sha
            or not after_sha
            or before_sha == after_sha
        ):
            raise ValueError(
                f"Golden case {case['id']} must contain two distinct before/after commit SHAs."
            )
        required_facts = case.get("required_facts", [])
        required_behaviors = case.get("required_behaviors", [])
        required_limitations = case.get("required_limitations", [])
        if not isinstance(required_facts, list) or not isinstance(
            required_behaviors, list
        ) or not isinstance(required_limitations, list) or not isinstance(
            case["forbidden_claims"], list
        ):
            raise ValueError(f"Golden case {case['id']} must use lists for evaluation criteria.")
        if not required_facts and not required_behaviors and not required_limitations:
            raise ValueError(
                f"Golden case {case['id']} needs required facts or required behaviors."
            )
        if not isinstance(case["expected_output"], dict):
            raise ValueError(f"Golden case {case['id']} expected_output must be an object.")
        shape_errors = _shape_failures(case, case["expected_output"])
        if shape_errors:
            raise ValueError(
                f"Golden case {case['id']} has invalid expected_output: "
                + "; ".join(shape_errors)
            )
    return cases


def load_system_prompt(path: Path = SYSTEM_PROMPT_PATH) -> str:
    try:
        prompt = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ValueError(f"Could not load system prompt at {path}: {error}") from error
    if not prompt:
        raise ValueError("System prompt is empty.")
    return prompt


def run_evaluation(mode: str = "mock") -> tuple[int, int, int]:
    cases = load_golden_set()
    system_prompt = load_system_prompt()
    adapter = build_adapter(mode)

    repeated_responses = {}
    hallucination_responses = {}
    for case in cases:
        responses = [
            adapter.generate_response(case, system_prompt)
            for _ in range(3)
        ]
        repeated_responses[case["id"]] = responses
        hallucination_responses[case["id"]] = responses[0]

    hallucination_results = evaluate_hallucination_suite(
        cases, hallucination_responses
    )
    consistency_results = evaluate_consistency_suite(cases, repeated_responses)
    hallucination_passed = sum(result["passed"] for result in hallucination_results)
    consistency_passed = sum(result["passed"] for result in consistency_results)
    total = len(cases)

    print(f"Evaluation mode: {adapter.mode} (mock results are not real-model results)")
    _print_results(
        "Hallucination / grounding",
        hallucination_results,
        hallucination_passed,
        total,
        HALLUCINATION_THRESHOLD,
    )
    _print_results(
        "Consistency (3 runs)",
        consistency_results,
        consistency_passed,
        total,
        CONSISTENCY_THRESHOLD,
    )
    overall_passed = (
        hallucination_passed / total >= HALLUCINATION_THRESHOLD
        and consistency_passed / total >= CONSISTENCY_THRESHOLD
    )
    print(f"\nOVERALL: {'PASS' if overall_passed else 'FAIL'}")
    return (
        0 if overall_passed else 1,
        hallucination_passed,
        consistency_passed,
    )


def _print_results(
    name: str,
    results: list[dict],
    passed: int,
    total: int,
    threshold: float,
) -> None:
    percentage = passed / total * 100
    required = math.ceil(total * threshold)
    print(f"\n{name}: {passed}/{total} ({percentage:.1f}%) - "
          f"threshold {threshold:.0%} ({required}/{total})")
    for result in results:
        if not result["passed"]:
            print(f"  FAIL {result['id']}:")
            for reason in result["failures"]:
                print(f"    - {reason}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("mock", "real"),
        default="mock",
        help="Use deterministic mock fixtures or the explicitly requested real adapter.",
    )
    args = parser.parse_args(argv)
    try:
        exit_code, _, _ = run_evaluation(args.mode)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Evaluation could not run: {error}", file=sys.stderr)
        return 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())