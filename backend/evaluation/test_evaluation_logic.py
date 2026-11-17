"""Tests for repository-grounding and repeated-analysis evaluation."""

from __future__ import annotations

import json
import unittest

from llm_adapter import build_adapter
from run_evaluation import load_golden_set
from test_consistency import evaluate_consistency
from test_hallucination import evaluate_hallucination


def encode(output: dict) -> str:
    return json.dumps(output)


class EvaluationLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_golden_set()
        cls.by_id = {case["id"]: case for case in cls.cases}

    def test_dataset_covers_required_repository_scenarios(self):
        self.assertGreaterEqual(len(self.cases), 15)
        expected = {
            "summary-single-file",
            "summary-multiple-files",
            "summary-added-file",
            "summary-deleted-file",
            "summary-bug-fix",
            "summary-docs-only",
            "summary-vague-message",
            "summary-misleading-message",
            "summary-incomplete-diff",
            "summary-empty-commit",
            "group-similar-commits",
            "group-unrelated-changes",
            "group-similar-message-different-changes",
            "group-different-message-similar-changes",
            "group-single-commit-history",
            "group-empty-history",
            "recommend-representative-captures",
            "visual-pair-difference",
            "visual-pair-incomplete",
        }
        self.assertTrue(expected.issubset(self.by_id))

    def test_mock_expected_outputs_pass_grounding(self):
        adapter = build_adapter("mock")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                response = adapter.generate_response(case, "")
                self.assertEqual(evaluate_hallucination(case, response), [])

    def test_incorrect_commit_summary_fails(self):
        case = self.by_id["summary-single-file"]
        response = dict(case["expected_output"])
        response["summary"] = "The navigation color changes to red."
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(failures)

    def test_fabricated_commit_identifier_fails(self):
        case = self.by_id["summary-single-file"]
        response = dict(case["expected_output"])
        response["commit_sha"] = "ffffffff"
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("invented or unsupported commit identifier" in f for f in failures))

    def test_fabricated_changed_file_fails(self):
        case = self.by_id["summary-single-file"]
        response = dict(case["expected_output"])
        response["files_changed"] = ["styles.css", "login.py"]
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("unsupported changed files" in f for f in failures))

    def test_fabricated_author_and_timestamp_fail(self):
        case = self.by_id["summary-single-file"]
        response = dict(case["expected_output"])
        response["summary"] += " Authored by Morgan on 2025-01-03T10:00:00Z."
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("unsupported commit author" in f for f in failures))
        self.assertTrue(any("unsupported timestamp" in f for f in failures))

    def test_misleading_commit_message_does_not_override_diff(self):
        case = self.by_id["summary-misleading-message"]
        response = dict(case["expected_output"])
        response["summary"] = "This fixes the security vulnerability."
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(failures)

    def test_missing_diff_requires_limitation_in_analysis(self):
        case = self.by_id["summary-incomplete-diff"]
        response = dict(case["expected_output"])
        response["limitations"] = []
        failures = evaluate_hallucination(case, encode(response))
        self.assertTrue(any("required limitation" in f for f in failures))

    def test_consistent_grouping_ignores_group_names_and_order(self):
        case = self.by_id["group-unrelated-changes"]
        first = json.loads(encode(case["expected_output"]))
        second = json.loads(encode(case["expected_output"]))
        third = json.loads(encode(case["expected_output"]))
        second["groups"][0]["title"] = "Footer color change"
        second["groups"][1]["title"] = "Validate email"
        third["groups"] = list(reversed(third["groups"]))
        third["groups"][0]["title"] = "Form validation"
        third["groups"][1]["title"] = "Footer appearance"
        responses = [encode(first), encode(second), encode(third)]
        self.assertEqual(evaluate_consistency(case, responses), [])

    def test_inconsistent_commit_groupings_fail(self):
        case = self.by_id["group-unrelated-changes"]
        correct = json.loads(encode(case["expected_output"]))
        incorrect = {
            "groups": [{
                "commit_shas": ["b220003", "b220004"],
                "title": "Shared work",
                "rationale": "Both changes belong together."
            }],
            "limitations": []
        }
        failures = evaluate_consistency(case, [encode(correct), encode(incorrect), encode(correct)])
        self.assertTrue(failures)

    def test_inconsistent_stated_limitations_fail(self):
        case = self.by_id["summary-incomplete-diff"]
        correct = dict(case["expected_output"])
        incorrect = dict(case["expected_output"])
        incorrect["limitations"] = []
        failures = evaluate_consistency(
            case, [encode(correct), encode(incorrect), encode(correct)]
        )
        self.assertTrue(failures)

    def test_consistently_wrong_response_does_not_pass_consistency(self):
        case = self.by_id["summary-single-file"]
        incorrect = dict(case["expected_output"])
        incorrect["summary"] = "The navigation changes to red."
        response = encode(incorrect)
        failures = evaluate_consistency(case, [response, response, response])
        self.assertTrue(failures)

    def test_real_mode_does_not_fall_back_to_mock(self):
        with self.assertRaisesRegex(RuntimeError, "will not be used as a fallback"):
            build_adapter("real")


if __name__ == "__main__":
    unittest.main()
