import copy
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from openai import APIConnectionError

from git_gallery_app.comparison_schema import ComparisonResult

from evals.compare.cases import Case, DiffContext, Rubric
from evals.compare.graders import ACCURACY, HALLUCINATION, failures, passed
from evals.compare.judge import (
    JUDGE_MODEL_ENV,
    JudgeError,
    JudgeVerdict,
    build_judge_input,
    judge_checks,
    request_verdict,
    validate_verdict,
)
from evals.compare.tests.test_case_format import VALID_DIFF

APP_NOTE = "Some source patches were shortened for the context limit."

RUBRIC = {
    "id": "header-and-footer",
    "description": "Header turns navy; footer text gets slightly smaller.",
    "expected_changes": [
        {"id": "header-bg", "element": "Header background", "before": "gray",
         "after": "navy", "expected_file_path": "styles.css"},
        {"id": "footer-size", "element": "Footer text", "before": "14px",
         "after": "12px", "required": False},
    ],
    "forbidden_claims": ["Gives a reason for the color change"],
    "required_limitations": ["Mentions the footer may be cut off"],
    "reference_output": {
        "changes": [{"element": "Header background", "location": "Top",
                     "file_path": "styles.css",
                     "description": "The header changes from gray to navy."}],
        "limitations": ["The footer may be cut off at the bottom."],
    },
}

ANSWER = ComparisonResult.model_validate({
    "changes": [
        {"element": "Header", "location": "Top", "file_path": "styles.css",
         "description": "The header background goes from gray to navy."},
    ],
    "limitations": ["The footer may be partly cut off."],
})

PERFECT_VERDICT = {
    "expected_changes": [
        {"expected_id": "header-bg", "status": "found", "matched_change_numbers": [1],
         "evidence": "goes from gray to navy"},
        {"expected_id": "footer-size", "status": "missing", "matched_change_numbers": [],
         "evidence": ""},
    ],
    "reported_changes": [
        {"change_number": 1, "matches_expected_id": "header-bg", "explanation": "header color"},
    ],
    "forbidden_claims": [{"claim_number": 1, "violated": False, "evidence": ""}],
    "required_limitations": [{"limitation_number": 1, "present": True,
                              "evidence": "footer may be partly cut off"}],
    "model_limitations": [{"limitation_number": 1, "restates_app_limitation": False}],
}


def make_case(rubric=None):
    diff = copy.deepcopy(VALID_DIFF)
    diff["limitations"] = [APP_NOTE]
    return Case(
        id="header-and-footer",
        directory=Path("unused"),
        before_png=Path("unused/before.png"),
        after_png=Path("unused/after.png"),
        diff=DiffContext.model_validate(diff),
        rubric=Rubric.model_validate(rubric or RUBRIC),
    )


def verdict(**overrides):
    data = copy.deepcopy(PERFECT_VERDICT)
    data.update(overrides)
    return JudgeVerdict.model_validate(data)


def failed_names(results):
    return {r.name for r in failures(results)}


class JudgeChecksTests(unittest.TestCase):
    def test_perfect_verdict_passes(self):
        results = judge_checks(make_case(), ANSWER, verdict())

        self.assertEqual(failures(results), [])

    def test_missing_optional_change_is_not_a_failure(self):
        results = judge_checks(make_case(), ANSWER, verdict())

        self.assertNotIn("found:footer-size", {r.name for r in results})

    def test_wrong_description_fails_both_categories(self):
        expected = copy.deepcopy(PERFECT_VERDICT["expected_changes"])
        expected[0]["status"] = "wrong"

        results = judge_checks(make_case(), ANSWER, verdict(expected_changes=expected))

        self.assertEqual(failed_names(results), {"correct_description:header-bg", "found:header-bg"})
        self.assertFalse(passed(results, HALLUCINATION))
        self.assertFalse(passed(results, ACCURACY))

    def test_missing_required_change_is_accuracy_only(self):
        expected = copy.deepcopy(PERFECT_VERDICT["expected_changes"])
        expected[0].update(status="missing", matched_change_numbers=[], evidence="")

        results = judge_checks(make_case(), ANSWER, verdict(expected_changes=expected))

        self.assertEqual(failed_names(results), {"found:header-bg"})
        self.assertTrue(passed(results, HALLUCINATION))

    def test_wrong_file_attribution_fails(self):
        answer = ANSWER.model_copy(deep=True)
        answer.changes[0].file_path = None

        results = judge_checks(make_case(), answer, verdict())

        self.assertEqual(failed_names(results), {"file_path:header-bg"})

    def test_invented_change_fails_unless_allowed(self):
        reported = [{"change_number": 1, "matches_expected_id": None, "explanation": "not in key"}]

        strict = judge_checks(make_case(), ANSWER, verdict(reported_changes=reported))
        lenient_rubric = {**RUBRIC, "allowed_extra_changes": 1}
        lenient = judge_checks(make_case(lenient_rubric), ANSWER, verdict(reported_changes=reported))

        self.assertIn("no_invented_changes", failed_names(strict))
        self.assertNotIn("no_invented_changes", failed_names(lenient))

    def test_forbidden_claim_fails(self):
        claims = [{"claim_number": 1, "violated": True, "evidence": "to look modern"}]

        results = judge_checks(make_case(), ANSWER, verdict(forbidden_claims=claims))

        self.assertEqual(failed_names(results), {"forbidden_claim:1"})

    def test_missing_required_limitation_fails(self):
        limits = [{"limitation_number": 1, "present": False, "evidence": ""}]

        results = judge_checks(make_case(), ANSWER, verdict(required_limitations=limits))

        self.assertEqual(failed_names(results), {"required_limitation:1"})

    def test_reworded_app_limitation_fails(self):
        limits = [{"limitation_number": 1, "restates_app_limitation": True}]

        results = judge_checks(make_case(), ANSWER, verdict(model_limitations=limits))

        self.assertEqual(failed_names(results), {"no_reworded_app_limitations"})


class ValidateVerdictTests(unittest.TestCase):
    def test_perfect_verdict_is_valid(self):
        validate_verdict(make_case(), ANSWER, verdict())

    def test_unknown_expected_id_is_rejected(self):
        expected = copy.deepcopy(PERFECT_VERDICT["expected_changes"])
        expected[1]["expected_id"] = "made-up"

        with self.assertRaisesRegex(JudgeError, "expected ids"):
            validate_verdict(make_case(), ANSWER, verdict(expected_changes=expected))

    def test_change_number_out_of_range_is_rejected(self):
        expected = copy.deepcopy(PERFECT_VERDICT["expected_changes"])
        expected[0]["matched_change_numbers"] = [2]

        with self.assertRaisesRegex(JudgeError, "does not exist"):
            validate_verdict(make_case(), ANSWER, verdict(expected_changes=expected))

    def test_found_without_matches_is_rejected(self):
        expected = copy.deepcopy(PERFECT_VERDICT["expected_changes"])
        expected[0]["matched_change_numbers"] = []

        with self.assertRaisesRegex(JudgeError, "'found' with matches"):
            validate_verdict(make_case(), ANSWER, verdict(expected_changes=expected))

    def test_skipped_answer_change_is_rejected(self):
        with self.assertRaisesRegex(JudgeError, "reported change numbers"):
            validate_verdict(make_case(), ANSWER, verdict(reported_changes=[]))

    def test_unknown_match_id_is_rejected(self):
        reported = [{"change_number": 1, "matches_expected_id": "nope", "explanation": ""}]

        with self.assertRaisesRegex(JudgeError, "unknown id"):
            validate_verdict(make_case(), ANSWER, verdict(reported_changes=reported))


class JudgeInputTests(unittest.TestCase):
    def test_input_numbers_answer_and_hides_file_expectations(self):
        data = build_judge_input(make_case(), ANSWER)

        self.assertEqual(data["answer"]["changes"][0]["number"], 1)
        self.assertEqual(data["answer"]["limitations"][0]["number"], 1)
        self.assertEqual(data["app_limitations"], [APP_NOTE])
        self.assertNotIn("expected_file_path", json.dumps(data))
        self.assertNotIn("required", data["expected_changes"][0])


class StrictSchemaTests(unittest.TestCase):
    """OpenAI strict mode: every object must forbid extra keys and require every key."""

    def test_judge_schema_is_strict_mode_compatible(self):
        schema = JudgeVerdict.model_json_schema()
        objects = [schema, *schema.get("$defs", {}).values()]

        for obj in objects:
            with self.subTest(obj=obj.get("title")):
                self.assertIs(obj.get("additionalProperties"), False)
                self.assertEqual(set(obj["required"]), set(obj["properties"]))


class RequestVerdictTests(unittest.TestCase):
    def fake_client(self, *, status="completed", output_text=None):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(
            status=status,
            output_text=output_text if output_text is not None else json.dumps(PERFECT_VERDICT),
        )
        return client

    def test_returns_validated_verdict(self):
        client = self.fake_client()

        result = request_verdict(make_case(), ANSWER, model="judge-model", client=client)

        self.assertEqual(result, verdict())
        body = client.responses.create.call_args.kwargs
        self.assertEqual(body["model"], "judge-model")
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertIs(body["store"], False)

    def test_model_comes_from_environment(self):
        client = self.fake_client()

        with patch.dict(os.environ, {JUDGE_MODEL_ENV: "env-judge"}):
            request_verdict(make_case(), ANSWER, client=client)

        self.assertEqual(client.responses.create.call_args.kwargs["model"], "env-judge")

    def test_missing_model_is_an_error(self):
        with patch.dict(os.environ, {JUDGE_MODEL_ENV: ""}):
            with self.assertRaisesRegex(JudgeError, JUDGE_MODEL_ENV):
                request_verdict(make_case(), ANSWER, client=self.fake_client())

    def test_incomplete_response_is_an_error(self):
        client = self.fake_client(status="incomplete")

        with self.assertRaisesRegex(JudgeError, "incomplete"):
            request_verdict(make_case(), ANSWER, model="m", client=client)

    def test_malformed_json_is_an_error(self):
        client = self.fake_client(output_text='{"expected_changes": "oops"}')

        with self.assertRaisesRegex(JudgeError, "does not match"):
            request_verdict(make_case(), ANSWER, model="m", client=client)

    def test_api_error_is_wrapped(self):
        client = Mock()
        client.responses.create.side_effect = APIConnectionError(request=Mock())

        with self.assertRaisesRegex(JudgeError, "APIConnectionError"):
            request_verdict(make_case(), ANSWER, model="m", client=client)