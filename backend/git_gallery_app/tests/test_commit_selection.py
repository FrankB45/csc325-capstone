import unittest

from ..commit_selection import (
    SelectionError,
    default_selection,
    validate_selection,
)

def shas(n):
    return [f"{i:040x}" for i in range(n)]


class DefaultSelectionTests(unittest.TestCase):
    def test_single_commit_selected_once(self):  # AC2
        h = shas(1)
        self.assertEqual(default_selection(h), h)

    def test_ten_or_fewer_selects_all(self):  # AC1
        for n in (2, 5, 10):
            self.assertEqual(default_selection(shas(n)), shas(n))

    def test_more_than_ten_picks_ten_distinct_with_ends(self):  # AC1
        for n in range(11, 51):
            h = shas(n)
            sel = default_selection(h)
            self.assertEqual(len(sel), 10, n)
            self.assertEqual(len(set(sel)), 10, n)
            self.assertEqual(sel[0], h[0])
            self.assertEqual(sel[-1], h[-1])
            self.assertEqual(sel, sorted(sel, key=h.index))  # stays in history order


class ValidateSelectionTests(unittest.TestCase):
    def test_empty_rejected(self):  # AC4
        with self.assertRaises(SelectionError) as c:
            validate_selection([], shas(5))
        self.assertEqual(c.exception.code, "selection_empty")

    def test_eleven_rejected(self):  # AC4
        with self.assertRaises(SelectionError) as c:
            validate_selection(shas(11), shas(20))
        self.assertEqual(c.exception.code, "selection_too_many")

    def test_unknown_and_duplicate_rejected(self):
        with self.assertRaises(SelectionError):
            validate_selection(["f" * 40], shas(5))
        with self.assertRaises(SelectionError):
            validate_selection([shas(5)[0]] * 2, shas(5))

    def test_boundaries_ok_and_ordered(self):
        h = shas(20)
        self.assertEqual(validate_selection([h[3]], h), [h[3]])
        self.assertEqual(validate_selection(list(reversed(h[:10])), h), h[:10])
