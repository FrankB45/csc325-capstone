"""Compare repeat analyses of the same selected commit pair."""

from __future__ import annotations

from test_hallucination import evaluate_hallucination, semantic_signature


def evaluate_consistency(case: dict, responses: list[str]) -> list[str]:
    """Require three structurally and substantively equivalent comparisons."""
    if len(responses) != 3:
        return [f"expected exactly 3 responses, received {len(responses)}"]

    signatures = [semantic_signature(case, response) for response in responses]
    failures = []
    if any(signature is None for signature in signatures):
        failures.append("one or more responses do not follow the compare_commits output format")
    elif not all(signature == signatures[0] for signature in signatures[1:]):
        failures.append(
            "repeated comparisons differ in commit pair, changed elements, "
            "before/after states, or limitations"
        )

    for index, response in enumerate(responses, start=1):
        accuracy_failures = evaluate_hallucination(case, response)
        if accuracy_failures:
            failures.append(
                f"run {index} is not evidence-grounded: {'; '.join(accuracy_failures)}"
            )
    return failures


def evaluate_consistency_suite(
    cases: list[dict],
    responses: dict[str, list[str]],
) -> list[dict]:
    results = []
    for case in cases:
        failures = evaluate_consistency(case, responses[case["id"]])
        results.append({"id": case["id"], "passed": not failures, "failures": failures})
    return results
