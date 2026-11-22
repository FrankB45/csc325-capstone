import copy
import json
import tempfile
import unittest
from pathlib import Path

from evals.compare.cases import (
    ANY_FILE,
    PNG_SIGNATURE,
    CaseFormatError,
    bias_pairs,
    load_case,
    load_dataset,
    DATASET_DIR,
    MIN_GOLDEN_CASES,
)

VALID_DIFF = {
    "page_path": "index.html",
    "before_sha": "a" * 40,
    "after_sha": "b" * 40,
    "files": [
        {
            "file_path": "styles.css",
            "previous_file_path": None,
            "status": "modified",
            "patch": "@@ -1 +1 @@\n-header { color: gray; }\n+header { color: navy; }",
            "patch_truncated": False,
        }
    ],
    "limitations": [],
}

VALID_RUBRIC = {
    "id": "header-color",
    "description": "Header changes from gray to navy.",
    "tags": ["color"],
    "expected_changes": [
        {
            "id": "header-bg",
            "element": "Header background",
            "before": "gray",
            "after": "navy",
            "expected_file_path": "styles.css",
        }
    ],
    "reference_output": {
    "changes": [
        {
            "element": "Header background",
            "location": "Top of the page",
            "file_path": "styles.css",
            "description": "The header background changes from gray to navy.",
        }
    ],
    "limitations": [],
    },
}


class CaseFormatTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_case(self, case_id="header-color", *, diff=None, rubric=None, pngs=True):
        folder = self.root / case_id
        folder.mkdir()
        (folder / "diff.json").write_text(json.dumps(diff or VALID_DIFF))
        (folder / "rubric.json").write_text(json.dumps(rubric or VALID_RUBRIC))
        if pngs:
            for name in ("before.png", "after.png"):
                (folder / name).write_bytes(PNG_SIGNATURE + b"fake image body")
        return folder

    def rubric_with(self, **changes):
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric.update(changes)
        return rubric

    # --- happy paths -------------------------------------------------------

    def test_valid_case_loads(self):
        case = load_case(self.write_case())

        self.assertEqual(case.id, "header-color")
        self.assertEqual(case.diff.supported_paths(), {"styles.css"})
        self.assertEqual(case.rubric.expected_changes[0].expected_file_path, "styles.css")

    def test_as_context_matches_production_shape(self):
        case = load_case(self.write_case())

        self.assertEqual(case.diff.as_context(), VALID_DIFF)

    def test_file_path_defaults_to_not_graded(self):
        rubric = copy.deepcopy(VALID_RUBRIC)
        del rubric["expected_changes"][0]["expected_file_path"]

        case = load_case(self.write_case(rubric=rubric))

        self.assertEqual(case.rubric.expected_changes[0].expected_file_path, ANY_FILE)

    def test_truncated_patch_can_be_expected(self):
        diff = copy.deepcopy(VALID_DIFF)
        diff["files"][0]["patch_truncated"] = True

        load_case(self.write_case(diff=diff))  # does not raise (decision D2)

    def test_expect_no_changes_case_loads(self):
        rubric = self.rubric_with(
            expect_no_changes=True,
            expected_changes=[],
            reference_output={"changes": [], "limitations": []},
        )

        case = load_case(self.write_case(rubric=rubric))

        self.assertTrue(case.rubric.expect_no_changes)

    # --- file problems -----------------------------------------------------

    def test_missing_png_is_rejected(self):
        with self.assertRaisesRegex(CaseFormatError, "missing before.png"):
            load_case(self.write_case(pngs=False))

    def test_non_png_is_rejected(self):
        folder = self.write_case()
        (folder / "after.png").write_bytes(b"GIF89a not a png")

        with self.assertRaisesRegex(CaseFormatError, "after.png is not a PNG"):
            load_case(folder)

    def test_folder_name_must_match_rubric_id(self):
        folder = self.write_case("other-name", rubric=self.rubric_with(id="header-color"))

        with self.assertRaisesRegex(CaseFormatError, "must match the folder name"):
            load_case(folder)

    # --- diff.json problems ------------------------------------------------

    def test_short_sha_is_rejected(self):
        diff = copy.deepcopy(VALID_DIFF)
        diff["before_sha"] = "a110001"

        with self.assertRaisesRegex(CaseFormatError, "before_sha"):
            load_case(self.write_case(diff=diff))

    def test_old_golden_set_key_names_are_rejected(self):
        diff = copy.deepcopy(VALID_DIFF)
        diff["source_context"] = diff.pop("files")

        with self.assertRaisesRegex(CaseFormatError, "source_context"):
            load_case(self.write_case(diff=diff))

    # --- rubric.json problems ----------------------------------------------

    def test_typo_in_rubric_field_is_rejected(self):
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric["expected_changes"][0]["requried"] = False

        with self.assertRaisesRegex(CaseFormatError, "requried"):
            load_case(self.write_case(rubric=rubric))

    def test_expected_file_must_have_a_patch(self):
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric["expected_changes"][0]["expected_file_path"] = "app.js"

        with self.assertRaisesRegex(CaseFormatError, "no patch for it"):
            load_case(self.write_case(rubric=rubric))

    def test_no_changes_case_cannot_list_changes(self):
        rubric = self.rubric_with(expect_no_changes=True)

        with self.assertRaisesRegex(CaseFormatError, "cannot list expected_changes"):
            load_case(self.write_case(rubric=rubric))

    def test_case_needs_a_required_change(self):
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric["expected_changes"][0]["required"] = False

        with self.assertRaisesRegex(CaseFormatError, "at least one required"):
            load_case(self.write_case(rubric=rubric))

    def test_duplicate_change_ids_are_rejected(self):
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric["expected_changes"].append(copy.deepcopy(rubric["expected_changes"][0]))

        with self.assertRaisesRegex(CaseFormatError, "duplicate expected change ids"):
            load_case(self.write_case(rubric=rubric))

    # --- reference_output problems -----------------------------------------

    def test_reference_output_must_match_production_schema(self):
        rubric = copy.deepcopy(VALID_RUBRIC)
        del rubric["reference_output"]["changes"][0]["location"]

        with self.assertRaisesRegex(CaseFormatError, "reference_output.changes.0.location"):
            load_case(self.write_case(rubric=rubric))

    def test_reference_output_file_must_have_a_patch(self):
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric["reference_output"]["changes"][0]["file_path"] = "made-up.css"

        with self.assertRaisesRegex(CaseFormatError, "reference_output change 1 cites"):
            load_case(self.write_case(rubric=rubric))

    def test_reference_output_must_not_repeat_app_limitations(self):
        note = "Git diff was unavailable; this comparison used screenshots only."
        diff = copy.deepcopy(VALID_DIFF)
        diff["limitations"] = [note]
        rubric = copy.deepcopy(VALID_RUBRIC)
        rubric["reference_output"]["limitations"] = [note]

        with self.assertRaisesRegex(CaseFormatError, "repeats limitations"):
            load_case(self.write_case(diff=diff, rubric=rubric))

    def test_no_changes_case_needs_empty_reference(self):
        rubric = self.rubric_with(expect_no_changes=True, expected_changes=[])

        with self.assertRaisesRegex(CaseFormatError, "empty reference_output.changes"):
            load_case(self.write_case(rubric=rubric))

    def test_changes_case_needs_reference_changes(self):
        rubric = self.rubric_with(reference_output={"changes": [], "limitations": []})

        with self.assertRaisesRegex(CaseFormatError, "cannot be empty"):
            load_case(self.write_case(rubric=rubric))
    
    # --- load_dataset ------------------------------------------------------

    def test_dataset_filters_by_tag_and_id(self):
        self.write_case("header-color")
        self.write_case("button-size", rubric=self.rubric_with(id="button-size", tags=["size"]))

        self.assertEqual([c.id for c in load_dataset(self.root)], ["button-size", "header-color"])
        self.assertEqual([c.id for c in load_dataset(self.root, tags=["size"])], ["button-size"])
        self.assertEqual([c.id for c in load_dataset(self.root, ids=["header-color"])], ["header-color"])

    # --- bias pairs --------------------------------------------------------

    def test_bias_pair_is_grouped(self):
        self.write_case("name-a", rubric=self.rubric_with(id="name-a", bias_pair="names"))
        self.write_case("name-b", rubric=self.rubric_with(id="name-b", bias_pair="names"))

        pairs = bias_pairs(load_dataset(self.root))

        self.assertEqual({k: [c.id for c in v] for k, v in pairs.items()},
                         {"names": ["name-a", "name-b"]})

    def test_bias_pair_needs_two_cases(self):
        self.write_case("name-a", rubric=self.rubric_with(id="name-a", bias_pair="names"))

        with self.assertRaisesRegex(CaseFormatError, "needs exactly 2 cases, found 1"):
            load_dataset(self.root)

    def test_bias_pair_must_share_expected_change_ids(self):
        other = self.rubric_with(id="name-b", bias_pair="names")
        other["expected_changes"] = copy.deepcopy(other["expected_changes"])
        other["expected_changes"][0]["id"] = "different-id"
        self.write_case("name-a", rubric=self.rubric_with(id="name-a", bias_pair="names"))
        self.write_case("name-b", rubric=other)

        with self.assertRaisesRegex(CaseFormatError, "same expected change ids"):
            load_dataset(self.root)


    def test_unknown_id_is_an_error(self):
        self.write_case()

        with self.assertRaisesRegex(CaseFormatError, "unknown case ids"):
            load_dataset(self.root, ids=["nope"])


class RealDatasetTests(unittest.TestCase):
    """Every case checked into dataset/ must load, and there must be enough."""

    def test_checked_in_dataset_is_valid(self):
        if not DATASET_DIR.is_dir() or not any(p.is_dir() for p in DATASET_DIR.iterdir()):
            self.skipTest("dataset/ has no cases yet (added in Step 8)")

        cases = load_dataset()

        self.assertGreaterEqual(len(cases), MIN_GOLDEN_CASES)