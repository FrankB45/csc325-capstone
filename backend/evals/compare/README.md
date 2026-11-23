# AI Compare evaluation

Checks that the AI Compare feature (two screenshots + a code diff → a list of
visual changes) gives answers that are correct, grounded, consistent, and fair.

## What it checks

| Check | Question it answers | Threshold |
|---|---|---|
| **hallucination** | Did the model say nothing wrong? (no invented changes, no wrong file paths, no forbidden claims) | 90% of cases |
| **accuracy** | Did the model find everything it should have? | 80% of cases |
| **consistency** | Does the same case pass or fail the same way on every run? | 80% of cases |
| **bias** | Do counterfactual twins (same change, different name/language/audience) get the same result? | 100% of pairs |

Each case runs 3 times. A case counts as passing a check only if **every** run passes.
The suite exits 0 when all four checks meet their thresholds, and 1 otherwise.

## How grading works

1. **Hard checks** (`graders.py`), plain code: is the answer valid, empty when
   nothing changed, and does it cite only files that are in the diff?
2. **LLM judge** (`judge.py`): a second model reads the answer and the case's
   rubric (text only, never the images) and marks each expected change as
   found / wrong / missing. Code turns that verdict into pass/fail checks.
3. **Scoring** (`scoring.py`): rolls the checks up per case and compares the
   results to the thresholds.

## Layout

    cases.py      loads and validates the dataset
    graders.py    hard checks
    judge.py      LLM judge
    run.py        the one command (live or offline)
    scoring.py    thresholds + final report
    dataset/      25 golden cases (see dataset/README.md)
    baseline.json a recorded passing run that CI re-grades
    results/      your local live runs (gitignored)
    tests/        unit tests for the suite itself

## Running it (from `backend/`)

Unit tests (no API, instant):

    python -m unittest discover -s evals/compare/tests -t .

Offline: re-grade a saved run with no API calls. This is what CI runs:

    python -m evals.compare.run --offline evals/compare/baseline.json

Live: calls OpenAI (25 cases × 3 runs, plus a judge call each). Needs
`OPENAI_API_KEY`, `OPENAI_MODEL` and `EVAL_JUDGE_MODEL` in `backend/.env`:

    python -m evals.compare.run
    python -m evals.compare.run --cases header-color --runs 1     # quick check
    OPENAI_MODEL=<model-id> python -m evals.compare.run            # try another model

Each live run saves a timestamped JSON file to `results/`.

## Reading results

Read the summary printed at the end first. It lists each check, its score,
and which cases failed. To look at one case, replay it offline:

    python -m evals.compare.run --offline evals/compare/results/<file>.json --cases <case-id>

Open the JSON only to see what the model actually said (`answer`) or why the
judge decided what it did (`verdict`).

## Changing things

- **Changed the system prompt, the model, or a rubric?** Do a full live run.
  If it passes, copy it over `baseline.json` and commit both. Old results
  files can't be replayed after a rubric changes.
- **Adding a case:** add a folder under `dataset/` (format in `dataset/README.md`),
  run the unit tests, then re-record the baseline.