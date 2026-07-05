"""Tests for the release version computer (tools/release.py, ADR 0007).

The bump is a pure function of the towncrier fragment types, so the tag and the
changelog can't drift. (Distinct from test_release.py, which covers the pack
release/build gate in aces_scenario_packs.release.)
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_MOD = Path(__file__).resolve().parents[1] / "tools" / "release.py"
_spec = importlib.util.spec_from_file_location("release_tool", _MOD)
rel = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = rel
_spec.loader.exec_module(rel)


class NextVersionTests(unittest.TestCase):
    def test_pre_1_0_added_or_removed_is_minor(self):
        self.assertEqual(rel.nxt((0, 1, 0), {"added"}), "0.2.0")
        self.assertEqual(rel.nxt((0, 1, 0), {"changed"}), "0.2.0")
        self.assertEqual(rel.nxt((0, 1, 0), {"deprecated"}), "0.2.0")
        self.assertEqual(rel.nxt((0, 1, 0), {"removed"}), "0.2.0")   # pre-1.0 caps to minor
        self.assertEqual(rel.nxt((0, 1, 0), {"breaking"}), "0.2.0")  # pre-1.0 caps to minor

    def test_pre_1_0_fixed_is_patch(self):
        self.assertEqual(rel.nxt((0, 1, 0), {"fixed"}), "0.1.1")
        self.assertEqual(rel.nxt((0, 1, 0), {"security"}), "0.1.1")

    def test_post_1_0(self):
        self.assertEqual(rel.nxt((1, 2, 3), {"removed"}), "2.0.0")
        self.assertEqual(rel.nxt((1, 2, 3), {"breaking"}), "2.0.0")
        self.assertEqual(rel.nxt((1, 2, 3), {"added"}), "1.3.0")
        self.assertEqual(rel.nxt((1, 2, 3), {"fixed"}), "1.2.4")

    def test_precedence_highest_wins(self):
        self.assertEqual(rel.nxt((1, 2, 3), {"fixed", "added", "removed"}), "2.0.0")
        self.assertEqual(rel.nxt((1, 2, 3), {"fixed", "added"}), "1.3.0")

    def test_no_or_unknown_types_is_none(self):
        self.assertIsNone(rel.nxt((1, 2, 3), set()))
        self.assertIsNone(rel.nxt((1, 2, 3), {"misc"}))

    def test_first_release_from_zero(self):
        self.assertEqual(rel.nxt((0, 0, 0), {"added"}), "0.1.0")
        self.assertEqual(rel.nxt((0, 0, 0), {"fixed"}), "0.0.1")


class CurrentVersionTests(unittest.TestCase):
    def test_cur_reads_the_literal(self):
        c = rel.cur()
        self.assertEqual(len(c), 3)
        self.assertTrue(all(isinstance(x, int) for x in c))


if __name__ == "__main__":
    unittest.main()
