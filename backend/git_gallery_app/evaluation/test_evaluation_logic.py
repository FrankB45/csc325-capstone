"""Tests for pair-comparison evaluation and mock adapter behavior."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy

from llm_adapter import build_adapter
from run_evaluation import load_golden_set, load_system_prompt
from test_consistency import evaluate_consistency
from test_hallucination import evaluate_hallucination


def encode(output: dict) -> str:
    return json.dumps(output)


class EvaluationLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_golden_set()
        cls.by_id = {case["id"]: case for case in cls.cases}

    def test_dataset_has_at_least_fifteen_pair_comparison_cases(self):
        self.assertGreaterEqual(len(self.cases), 15)
        self.assertEqual({case["task"]["id"] for case in self.cases}, {"compare_commits"})

    def test_prompt_is_loaded_from_app_prompts_folder(self):
        self.assertTrue(load_system_prompt().strip())

    def test_mock_expected_outputs_pass_grounding(self):
        adapter = build_adapter("mock")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                response = adapter.generate_response(case, "")
                self.assertEqual(evaluate_hallucination(case, response), [])

    def test_wrong_commit_pair_fails(self):
        case = self.by_id["compare-header-color"]
        response = deepcopy(case["expected_output"])
        response["after_commit_sha"] = "ffffffff"
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("selected after commit" in failure for failure in failures))

    def test_incorrect_visual_change_fails(self):
        case = self.by_id["compare-header-color"]
        response = deepcopy(case["expected_output"])
        response["changes"] = [{
            "element": "Header background",
            "before": "Gray",
            "after": "Red",
            "evidence": "The header becomes red."
        }]
        self.assertTrue(evaluate_hallucination(case, encode(response)))

    def test_fabricated_commit_identifier_fails(self):
        case = self.by_id["compare-header-color"]
        response = deepcopy(case["expected_output"])
        response["changes"][0]["evidence"] += " Commit abcdef0 confirms it."
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("unsupported commit identifier" in failure for failure in failures))

    def test_empty_change_list_requires_limit_or_no_difference_reason(self):
        case = self.by_id["compare-header-color"]
        response = {
            "before_commit_sha": "a110001",
            "after_commit_sha": "a110002",
            "changes": [],
            "limitations": []
        }
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("empty change list" in failure for failure in failures))

    def test_no_visible_changes_are_accepted_when_explained(self):
        case = self.by_id["compare-identical-screenshots"]
        response = case["expected_output"]
        self.assertEqual(evaluate_hallucination(case, encode(response)), [])

    def test_consistency_allows_change_order_variation(self):
        case = self.by_id["compare-multiple-elements"]
        first = json.loads(encode(case["expected_output"]))
        second = json.loads(encode(case["expected_output"]))
        third = json.loads(encode(case["expected_output"]))
        second["changes"] = list(reversed(second["changes"]))
        third["changes"][0]["element"] = "Card corners"
        third["changes"][1]["element"] = "Product button text"
        third["changes"] = list(reversed(third["changes"]))
        third["changes"][0]["evidence"] = (
            "The screenshot shows rounded corners on the product card."
        )
        third["changes"][1]["evidence"] = (
            "The button label changes from Buy to Buy now between screenshots."
        )
        self.assertEqual(
            evaluate_consistency(case, [encode(first), encode(second), encode(third)]),
            [],
        )

    def test_inconsistent_commit_comparisons_fail(self):
        case = self.by_id["compare-header-color"]
        correct = json.loads(encode(case["expected_output"]))
        wrong = json.loads(encode(case["expected_output"]))
        wrong["changes"][0]["after"] = "Red"
        wrong["changes"][0]["evidence"] = "The header changes from gray to red."
        failures = evaluate_consistency(case, [encode(correct), encode(wrong), encode(correct)])
        self.assertTrue(failures)

    def test_consistently_wrong_comparisons_do_not_pass_consistency(self):
        case = self.by_id["compare-header-color"]
        wrong = json.loads(encode(case["expected_output"]))
        wrong["changes"][0]["after"] = "Red"
        wrong["changes"][0]["evidence"] = "The header changes from gray to red."
        response = encode(wrong)
        self.assertTrue(evaluate_consistency(case, [response, response, response]))

    def test_real_mode_does_not_fall_back_to_mock(self):
        with self.assertRaisesRegex(RuntimeError, "will not be used as a fallback"):
            build_adapter("real")


if __name__ == "__main__":
    unittest.main()
