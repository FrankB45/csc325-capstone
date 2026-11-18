from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from openai import APIConnectionError, APITimeoutError

from ..models import Capture, Comparison
from ..services import comparisons, llm


@override_settings(
    OPENAI_API_KEY="test-key",
    OPENAI_MODEL="test-model",
)
class ComparisonServiceTests(SimpleTestCase):
    def setUp(self):
        job = SimpleNamespace(captures=[
            Capture(
                commit_sha="a" * 40,
                position=0,
                status=Capture.Status.COMPLETE,
                screenshot_path="test/before.png",
            ),
            Capture(
                commit_sha="b" * 40,
                position=1,
                status=Capture.Status.COMPLETE,
                screenshot_path="test/after.png",
            ),
        ])
        self.record = SimpleNamespace(
            pk="test-comparison",
            capture_job=job,
            before_position=0,
            after_position=1,
            status=Comparison.Status.QUEUED,
            attempts=0,
            refresh_from_db=Mock(),
        )
        self.queryset = Mock()
        self.queryset.update.return_value = 1

        self.patch(Comparison.objects, "get", return_value=self.record)
        self.patch(Comparison.objects, "filter", return_value=self.queryset)

        self.prompt_loader = self.patch(
            comparisons,
            "load_system_prompt",
            return_value=("Test system prompt", "system_prompt_v1"),
        )
        self.patch(
            llm,
            "_png_data_url",
            return_value="data:image/png;base64,dGVzdA==",
        )

        self.openai = self.patch(llm, "OpenAI")
        self.client = self.openai.return_value.__enter__.return_value
        self.response = SimpleNamespace(
            status="completed",
            output=[],
            output_text='{"changes": [], "limitations": []}',
        )
        self.client.responses.create.return_value = self.response

    def patch(self, target, name, **kwargs):
        patcher = patch.object(target, name, **kwargs)
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        return mocked

    def process(self):
        comparisons.process_comparison(self.record.pk)
        return self.queryset.update.call_args.kwargs

    def assert_failed(self, code, *, llm_failure=True):
        saved = self.process()

        self.assertEqual(saved["status"], Comparison.Status.FAILED)
        self.assertEqual(saved["error_code"], code)
        self.assertTrue(saved["error_message"])
        self.assertIsNone(saved["result"])
        self.assertIsNone(saved["result_source"])

        if llm_failure:
            self.assertEqual(saved["llm_error"]["code"], code)
        else:
            self.assertIsNone(saved["llm_error"])

    def test_success_uses_prompt_text_and_saves_version(self):
        saved = self.process()

        self.assertEqual(saved["status"], Comparison.Status.COMPLETE)
        self.assertEqual(saved["result_source"], Comparison.Source.LLM)
        self.assertEqual(saved["prompt_version"], "system_prompt_v1")
        self.assertEqual(
            saved["result"],
            {"changes": [], "limitations": []},
        )
        self.assertEqual(saved["error_code"], "")
        self.assertIsNone(saved["llm_error"])
        self.prompt_loader.assert_called_once_with()

        self.assertEqual(
            self.client.responses.create.call_args.kwargs["instructions"],
            "Test system prompt",
        )

    def test_timeout_is_saved_as_failure(self):
        self.client.responses.create.side_effect = APITimeoutError(
            request=Mock()
        )
        self.assert_failed("openai_timeout")

    def test_connection_error_is_saved_as_failure(self):
        self.client.responses.create.side_effect = APIConnectionError(
            request=Mock()
        )
        self.assert_failed("openai_connection")

    def test_invalid_json_is_saved_as_failure(self):
        self.response.output_text = "not JSON"
        self.assert_failed("invalid_response")

    def test_invalid_response_shape_is_saved_as_failure(self):
        self.response.output_text = '{"changes": []}'
        self.assert_failed("invalid_response")

    def test_missing_prompt_prevents_api_call(self):
        self.prompt_loader.side_effect = llm.ComparisonRequestError(
            "prompt_unavailable",
            "The configured system prompt could not be read.",
        )

        self.assert_failed("prompt_unavailable", llm_failure=False)
        self.openai.assert_not_called()

    def test_completed_comparison_is_reused(self):
        self.record.status = Comparison.Status.COMPLETE

        result = comparisons.process_comparison(self.record.pk)

        self.assertIs(result, self.record)
        self.queryset.update.assert_not_called()
        self.prompt_loader.assert_not_called()
        self.openai.assert_not_called()

    def test_lost_claim_does_not_call_api(self):
        self.queryset.update.return_value = 0

        comparisons.process_comparison(self.record.pk)

        self.queryset.update.assert_called_once()
        self.prompt_loader.assert_not_called()
        self.openai.assert_not_called()

    @override_settings(
        SYSTEM_PROMPT_PATH="git_gallery_app/prompts/system_prompt_v2.txt"
    )
    def test_loader_reads_configured_file_and_returns_version(self):
        with patch.object(
            Path,
            "read_text",
            autospec=True,
            return_value=" Prompt text \n",
        ) as read:
            text, version = llm.load_system_prompt()

        self.assertEqual(text, "Prompt text")
        self.assertEqual(version, "system_prompt_v2")
        self.assertEqual(
            read.call_args.args[0],
            settings.BASE_DIR / settings.SYSTEM_PROMPT_PATH,
        )