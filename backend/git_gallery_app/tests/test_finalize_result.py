from django.test import SimpleTestCase

from ..comparison_schema import ComparisonChange, ComparisonResult
from ..services.comparisons import UNVERIFIED_FILE_LIMITATION, finalize_result

SOURCE_NOTE = "Source context includes only HTML, CSS, and JavaScript."


def make_change(file_path, element="Header"):
    return ComparisonChange(
        element=element,
        location="Top of the page",
        file_path=file_path,
        description="The header changes from gray to navy.",
    )


def make_context(files=(), limitations=()):
    return {
        "page_path": "index.html",
        "before_sha": "a" * 40,
        "after_sha": "b" * 40,
        "files": list(files),
        "limitations": list(limitations),
    }


def file_entry(path, patch="@@ -1 +1 @@\n-a\n+b", truncated=False):
    return {
        "file_path": path,
        "previous_file_path": None,
        "status": "modified",
        "patch": patch,
        "patch_truncated": truncated,
    }


class FinalizeResultTests(SimpleTestCase):
    def test_supported_file_path_is_kept(self):
        raw = ComparisonResult(changes=[make_change("styles.css")], limitations=[])
        context = make_context(files=[file_entry("styles.css")])

        result = finalize_result(raw, context)

        self.assertEqual(result.changes[0].file_path, "styles.css")
        self.assertEqual(result.limitations, [])

    def test_truncated_patch_still_supports_file_path(self):
        raw = ComparisonResult(changes=[make_change("styles.css")], limitations=[])
        context = make_context(files=[file_entry("styles.css", truncated=True)])

        result = finalize_result(raw, context)

        self.assertEqual(result.changes[0].file_path, "styles.css")

    def test_file_without_patch_text_is_cleared(self):
        raw = ComparisonResult(changes=[make_change("app.js")], limitations=[])
        context = make_context(files=[file_entry("app.js", patch=None)])

        result = finalize_result(raw, context)

        self.assertIsNone(result.changes[0].file_path)
        self.assertEqual(result.limitations, [UNVERIFIED_FILE_LIMITATION])

    def test_invented_file_path_is_cleared(self):
        raw = ComparisonResult(changes=[make_change("made-up.css")], limitations=[])
        context = make_context(files=[file_entry("styles.css")])

        result = finalize_result(raw, context)

        self.assertIsNone(result.changes[0].file_path)
        self.assertIn(UNVERIFIED_FILE_LIMITATION, result.limitations)

    def test_null_file_path_is_left_alone(self):
        raw = ComparisonResult(changes=[make_change(None)], limitations=[])

        result = finalize_result(raw, make_context())

        self.assertIsNone(result.changes[0].file_path)
        self.assertEqual(result.limitations, [])

    def test_limitations_are_merged_in_order_without_duplicates(self):
        raw = ComparisonResult(
            changes=[make_change("one.css"), make_change("two.css", element="Footer")],
            limitations=["The page may still be loading.", SOURCE_NOTE],
        )
        context = make_context(limitations=[SOURCE_NOTE])

        result = finalize_result(raw, context)

        self.assertEqual(result.limitations, [
            "The page may still be loading.",
            SOURCE_NOTE,
            UNVERIFIED_FILE_LIMITATION,
        ])

    def test_inputs_are_not_modified(self):
        raw = ComparisonResult(changes=[make_change("made-up.css")], limitations=[])
        context = make_context(limitations=[SOURCE_NOTE])

        finalize_result(raw, context)

        self.assertEqual(raw.changes[0].file_path, "made-up.css")
        self.assertEqual(raw.limitations, [])
        self.assertEqual(context["limitations"], [SOURCE_NOTE])