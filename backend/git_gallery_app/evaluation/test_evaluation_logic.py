"""Tests for the compare-two-commits evaluation contract."""

from __future__ import annotations

import copy
import json
import unittest

from llm_adapter import build_adapter
from run_evaluation import load_golden_set, load_system_prompt
from test_consistency import evaluate_consistency
from test_hallucination import evaluate_hallucination

from unittest.mock import patch

from django.conf import settings


def encode(output: dict) -> str:
    return json.dumps(output)


class EvaluationLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_golden_set()
        cls.by_id = {case["id"]: case for case in cls.cases}

    def test_dataset_uses_only_compare_commits_cases(self):
        self.assertGreaterEqual(len(self.cases), 15)
        self.assertEqual({case["task"]["id"] for case in self.cases}, {"compare_commits"})

    @patch.object(
        settings,
        "SYSTEM_PROMPT_PATH",
        "git_gallery_app/prompts/system_prompt_v2.txt",
    )
    def test_prompt_is_loaded(self):
        prompt, version = load_system_prompt()

        self.assertEqual(version, "system_prompt_v2")
        self.assertIn("exactly one JSON object", prompt)
        self.assertIn("file_path", prompt)

    def test_mock_expected_outputs_pass_grounding(self):
        adapter = build_adapter("mock")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    evaluate_hallucination(case, adapter.generate_response(case, "")),
                    [],
                )

    def test_response_must_not_include_old_commit_id_fields(self):
        case = self.by_id["compare-header-color"]
        response = copy.deepcopy(case["expected_output"])
        response["before_commit_sha"] = case["repository_data"]["before_commit_sha"]
        failures = evaluate_hallucination(case, encode(response))
        self.assertIn("before_commit_sha: extra_forbidden", failures)

    def test_change_requires_exact_four_fields(self):
        case = self.by_id["compare-header-color"]
        response = copy.deepcopy(case["expected_output"])
        del response["changes"][0]["location"]
        failures = evaluate_hallucination(case, encode(response))
        self.assertIn("changes.0.location: missing", failures)

    def test_supported_file_path_passes(self):
        case = self.by_id["compare-header-color"]
        response = copy.deepcopy(case["expected_output"])
        self.assertEqual(evaluate_hallucination(case, encode(response)), [])

    def test_unsupported_file_path_fails(self):
        case = self.by_id["compare-header-color"]
        response = copy.deepcopy(case["expected_output"])
        response["changes"][0]["file_path"] = "other.css"
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("unsupported or truncated file_path" in failure for failure in failures))

    def test_truncated_patch_forbids_file_attribution(self):
        case = self.by_id["compare-truncated-patch"]
        response = copy.deepcopy(case["expected_output"])
        response["changes"][0]["file_path"] = "styles.css"
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("unsupported or truncated file_path" in failure for failure in failures))

    def test_missing_screenshot_must_return_empty_changes(self):
        case = self.by_id["compare-missing-before"]
        response = copy.deepcopy(case["expected_output"])
        response["changes"] = [{
            "element": "Save button",
            "location": None,
            "file_path": None,
            "description": "A button is visible.",
        }]
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("unavailable screenshot evidence" in failure for failure in failures))

    def test_missing_file_connection_uses_null(self):
        case = self.by_id["compare-missing-diff-file-attribution"]
        response = copy.deepcopy(case["expected_output"])
        self.assertEqual(evaluate_hallucination(case, encode(response)), [])

    def test_inconsistent_comparisons_fail_consistency(self):
        case = self.by_id["compare-header-color"]
        correct = copy.deepcopy(case["expected_output"])
        wrong = copy.deepcopy(correct)
        wrong["changes"][0]["description"] = "The header changes from gray to red."
        failures = evaluate_consistency(case, [encode(correct), encode(wrong), encode(correct)])
        self.assertTrue(failures)

    def test_consistently_wrong_comparison_does_not_pass(self):
        case = self.by_id["compare-header-color"]
        wrong = copy.deepcopy(case["expected_output"])
        wrong["changes"][0]["description"] = "The header changes from gray to red."
        failures = evaluate_consistency(case, [encode(wrong), encode(wrong), encode(wrong)])
        self.assertTrue(failures)

    def test_real_mode_does_not_fall_back_to_mock(self):
        with self.assertRaisesRegex(RuntimeError, "will not be used as a fallback"):
            build_adapter("real")


if __name__ == "__main__":
    unittest.main()
