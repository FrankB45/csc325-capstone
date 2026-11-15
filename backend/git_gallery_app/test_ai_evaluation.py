import json
from unittest import TestCase

from evals.run import CASES_PATH, evaluate, response_is_valid


class MockedAiResponseTests(TestCase):
    def test_mock_responses_match_the_selection_contract(self):
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

        self.assertTrue(all(ok for _, ok in evaluate(cases)))

    def test_non_object_response_is_rejected(self):
        self.assertFalse(response_is_valid(None, ["a" * 40]))

    def test_response_with_missing_selection_is_rejected(self):
        self.assertFalse(response_is_valid({}, ["a" * 40]))
