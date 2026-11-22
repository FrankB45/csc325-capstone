import copy
import unittest
from pathlib import Path

from git_gallery_app.comparison_schema import ComparisonResult

from evals.compare.cases import DATASET_DIR, Case, DiffContext, Rubric, load_dataset
from evals.compare.graders import (
    ACCURACY,
    FORMAT,
    HALLUCINATION,
    RunOutput,
    failures,
    passed,
    run_hard_checks,
)
from evals.compare.tests.test_case_format import VALID_DIFF, VALID_RUBRIC

APP_NOTE = "Some source patches were shortened for the context limit."


def make_case(diff=None, rubric=None):
    """Build a Case in memory (no files needed for these checks)."""
    return Case(
        id="header-color",
        directory=Path("unused"),
        before_png=Path("unused/before.png"),
        after_png=Path("unused/after.png"),
        diff=DiffContext.model_validate(diff or VALID_DIFF),
        rubric=Rubric.model_validate(rubric or VALID_RUBRIC),
    )


def answer(changes=None, limitations=None):
    reference = copy.deepcopy(VALID_RUBRIC["reference_output"])
    if changes is not None:
        reference["changes"] = changes
    if limitations is not None:
        reference["limitations"] = limitations
    return RunOutput(raw=ComparisonResult.model_validate(reference))


def change(file_path="styles.css"):
    return {
        "element": "Header background",
        "location": "Top of the page",
        "file_path": file_path,
        "description": "The header background changes from gray to navy.",
    }


def failed_names(results):
    return {result.name for result in failures(results)}


class HardCheckTests(unittest.TestCase):
    def test_reference_answer_passes_everything(self):
        results = run_hard_checks(make_case(), answer())

        self.assertEqual(failures(results), [])

    def test_model_error_is_a_format_failure(self):
        results = run_hard_checks(make_case(), RunOutput(raw=None, error_code="invalid_response"))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].category, FORMAT)
        self.assertIn("invalid_response", results[0].detail)

    # --- file_paths_grounded -----------------------------------------------

    def test_invented_file_is_hallucination(self):
        results = run_hard_checks(make_case(), answer(changes=[change("made-up.css")]))

        self.assertEqual(failed_names(results), {"file_paths_grounded"})
        self.assertFalse(passed(results, HALLUCINATION))
        self.assertTrue(passed(results, ACCURACY))

    def test_null_file_path_is_always_grounded(self):
        results = run_hard_checks(make_case(), answer(changes=[change(None)]))

        self.assertEqual(failures(results), [])

    def test_file_without_patch_text_is_not_grounded(self):
        diff = copy.deepcopy(VALID_DIFF)
        diff["files"][0]["patch"] = None
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric["expected_changes"][0]["expected_file_path"] = None
        rubric["reference_output"]["changes"][0]["file_path"] = None

        results = run_hard_checks(make_case(diff, rubric), answer(changes=[change("styles.css")]))

        self.assertIn("file_paths_grounded", failed_names(results))

    def test_truncated_patch_still_grounds_a_file(self):
        diff = copy.deepcopy(VALID_DIFF)
        diff["files"][0]["patch_truncated"] = True

        results = run_hard_checks(make_case(diff), answer())

        self.assertEqual(failures(results), [])  # decision D2

    # --- empty / non-empty -------------------------------------------------

    def test_change_on_unchanged_page_is_hallucination(self):
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric.update(
            expect_no_changes=True,
            expected_changes=[],
            reference_output={"changes": [], "limitations": []},
        )

        results = run_hard_checks(make_case(rubric=rubric), answer())

        self.assertEqual(failed_names(results), {"empty_when_no_change"})

    def test_empty_answer_on_changed_page_is_an_accuracy_failure(self):
        results = run_hard_checks(make_case(), answer(changes=[]))

        self.assertEqual(failed_names(results), {"reports_changes"})
        self.assertTrue(passed(results, HALLUCINATION))
        self.assertFalse(passed(results, ACCURACY))

    # --- no_repeated_app_limitations (decision D4) --------------------------

    def test_repeating_an_app_limitation_fails(self):
        diff = copy.deepcopy(VALID_DIFF)
        diff["limitations"] = [APP_NOTE]
        sloppy_copy = "  some source patches were SHORTENED for the context limit "

        results = run_hard_checks(make_case(diff), answer(limitations=[sloppy_copy]))

        self.assertEqual(failed_names(results), {"no_repeated_app_limitations"})

    def test_models_own_limitation_is_fine(self):
        diff = copy.deepcopy(VALID_DIFF)
        diff["limitations"] = [APP_NOTE]

        results = run_hard_checks(
            make_case(diff),
            answer(limitations=["The after screenshot may still be loading."]),
        )

        self.assertEqual(failures(results), [])

    # --- helpers -----------------------------------------------------------

    def test_passed_with_no_categories_means_everything(self):
        results = run_hard_checks(make_case(), answer(changes=[]))

        self.assertFalse(passed(results))
        self.assertTrue(passed(results, FORMAT, HALLUCINATION))


class ReferenceCalibrationTests(unittest.TestCase):
    """Every hand-written reference answer must pass every hard check.

    If one fails, either the reference answer or a grader is wrong.
    """

    def test_reference_outputs_pass_hard_checks(self):
        if not DATASET_DIR.is_dir() or not any(p.is_dir() for p in DATASET_DIR.iterdir()):
            self.skipTest("dataset/ has no cases yet (added in Step 8)")

        for case in load_dataset():
            with self.subTest(case=case.id):
                results = run_hard_checks(case, RunOutput(raw=case.rubric.reference_output))
                self.assertEqual(failures(results), [])