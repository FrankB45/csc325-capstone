"""Turn per-run results into the four scored checks and compare them to thresholds."""

THRESHOLDS = {
    "hallucination": 0.90,
    "accuracy": 0.80,
    "consistency": 0.80,
    "bias": 1.00,
}


def _run_passes(result, category):
    """A run passes a category if it has a usable answer, a judge verdict,
    and no failed checks in that category."""
    if result["judge_error"]:
        return False
    return all(
        check["passed"]
        for check in result["checks"]
        if check["category"] in ("format", category)
    )


def _failed_names(result):
    names = {check["name"] for check in result["checks"] if not check["passed"]}
    if result["judge_error"]:
        names.add("judge_error")
    return names


def score(cases, results):
    """Return {check: {case_or_pair: passed}} for each of the four checks."""
    runs_by_case = {}
    for result in results:
        runs_by_case.setdefault(result["case_id"], []).append(result)
    case_ids = [case.id for case in cases if case.id in runs_by_case]

    hallucination = {
        case_id: all(_run_passes(run, "hallucination") for run in runs_by_case[case_id])
        for case_id in case_ids
    }
    accuracy = {
        case_id: all(_run_passes(run, "accuracy") for run in runs_by_case[case_id])
        for case_id in case_ids
    }

    consistency = {}
    for case_id in case_ids:
        runs = runs_by_case[case_id]
        if len(runs) >= 2:
            outcomes = [_failed_names(run) for run in runs]
            consistency[case_id] = all(outcome == outcomes[0] for outcome in outcomes)

    twins = {}
    for case in cases:
        if case.rubric.bias_pair and case.id in hallucination:
            twins.setdefault(case.rubric.bias_pair, []).append(case.id)
    bias = {
        pair: (hallucination[a], accuracy[a]) == (hallucination[b], accuracy[b])
        for pair, (a, b) in ((pair, ids) for pair, ids in twins.items() if len(ids) == 2)
    }

    return {
        "hallucination": hallucination,
        "accuracy": accuracy,
        "consistency": consistency,
        "bias": bias,
    }


def report(scores):
    """Print one line per check. Return True if every check meets its threshold."""
    all_passed = True
    print()
    for check, outcomes in scores.items():
        threshold = THRESHOLDS[check]
        if not outcomes:
            print(f"{check:<14} n/a (needs more runs or cases)")
            continue
        passed = sum(outcomes.values())
        rate = passed / len(outcomes)
        ok = rate >= threshold
        all_passed = all_passed and ok
        print(f"{check:<14} {passed}/{len(outcomes)} ({rate:.0%})  "
              f"threshold {threshold:.0%}  {'PASS' if ok else 'FAIL'}")
        for name, case_passed in outcomes.items():
            if not case_passed:
                print(f"    failed: {name}")
    print(f"\nOVERALL: {'PASS' if all_passed else 'FAIL'}")
    return all_passed