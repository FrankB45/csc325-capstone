"""Run the AI Compare evaluation.

From backend/:
    python -m evals.compare.run                                  # live: calls OpenAI
    python -m evals.compare.run --cases header-color --runs 1    # live, small
    python -m evals.compare.run --offline evals/compare/baseline.json   # no API calls (CI)
"""

import argparse
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from git_gallery_app.comparison_schema import ComparisonResult
from git_gallery_app.services.llm import ComparisonRequestError

from .cases import load_dataset
from .graders import RunOutput, run_hard_checks
from .judge import JudgeError, JudgeVerdict, judge_checks, request_verdict
from .scoring import report, score


RESULTS_DIR = Path(__file__).resolve().parent / "results"


def grade(case, output, verdict):
    """Hard checks always; judge checks when there is a verdict."""
    checks = run_hard_checks(case, output)
    if output.raw is not None and verdict is not None:
        checks += judge_checks(case, output.raw, verdict)
    return [asdict(check) for check in checks]


def run_once(case, system_prompt, compare, judge):
    """Live: ask the model and the judge about one case, return a JSON-ready dict."""
    try:
        raw = compare(
            case.before_png,
            case.after_png,
            system_prompt,
            diff_context=json.dumps(case.diff.as_context(), ensure_ascii=False),
        )
        output = RunOutput(raw=raw)
    except ComparisonRequestError as error:
        output = RunOutput(raw=None, error_code=error.code)

    verdict = None
    judge_error = None
    if output.raw is not None:
        for _ in range(2):  # the judge occasionally returns a malformed verdict; try once more
            try:
                verdict = judge(case, output.raw)
                judge_error = None
                break
            except JudgeError as error:
                judge_error = str(error)

    return {
        "case_id": case.id,
        "answer": output.raw.model_dump(mode="json") if output.raw else None,
        "error_code": output.error_code,
        "verdict": verdict.model_dump(mode="json") if verdict else None,
        "judge_error": judge_error,
        "checks": grade(case, output, verdict),
    }


def regrade(case, saved):
    """Offline: grade a saved result again without calling any API."""
    output = RunOutput(
        raw=ComparisonResult.model_validate(saved["answer"]) if saved["answer"] else None,
        error_code=saved["error_code"],
    )
    verdict = JudgeVerdict.model_validate(saved["verdict"]) if saved["verdict"] else None
    return {**saved, "checks": grade(case, output, verdict)}


def print_result(result):
    failed = [check for check in result["checks"] if not check["passed"]]
    status = "pass" if not failed and not result["judge_error"] else "FAIL"
    print(f"{result['case_id']} run {result['run']}: {status}")
    for check in failed:
        print(f"    {check['name']}: {check['detail']}")
    if result["judge_error"]:
        print(f"    judge error: {result['judge_error']}")


def run_live(cases, runs):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from git_gallery_app.services.comparisons import compare_screenshots
    from git_gallery_app.services.llm import load_system_prompt

    system_prompt, prompt_version = load_system_prompt()

    results = []
    for case in cases:
        for run in range(1, runs + 1):
            result = run_once(case, system_prompt, compare_screenshots, request_verdict)
            result["run"] = run
            results.append(result)
            print_result(result)

    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{datetime.now():%Y-%m-%d_%H%M%S}_{settings.OPENAI_MODEL}.json"
    path.write_text(json.dumps({
        "model": settings.OPENAI_MODEL,
        "prompt_version": prompt_version,
        "results": results,
    }, indent=2))
    print(f"\nSaved {path}")
    return results


def run_offline(cases, results_file):
    cases_by_id = {case.id: case for case in cases}
    saved = json.loads(Path(results_file).read_text())

    results = []
    for saved_result in saved["results"]:
        case = cases_by_id.get(saved_result["case_id"])
        if case is None:
            continue  # case was removed or filtered out with --cases
        result = regrade(case, saved_result)
        results.append(result)
        print_result(result)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m evals.compare.run")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--cases", nargs="+", metavar="ID")
    parser.add_argument("--offline", metavar="RESULTS_FILE",
                        help="re-grade a saved results file without calling any API")
    args = parser.parse_args(argv)

    cases = load_dataset(ids=args.cases)
    if args.offline:
        results = run_offline(cases, args.offline)
    else:
        results = run_live(cases, args.runs)
    return 0 if report(score(cases, results)) else 1


if __name__ == "__main__":
    raise SystemExit(main())