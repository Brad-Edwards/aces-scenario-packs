"""Tests for the changelog-driven version computer (tools/release_bump.py).

The version is a pure function of the fragment types, so the tag and the
changelog can't drift (ADR 0007).
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_MOD = Path(__file__).resolve().parents[1] / "tools" / "release_bump.py"
_spec = importlib.util.spec_from_file_location("release_bump", _MOD)
rb = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = rb
_spec.loader.exec_module(rb)


class BumpLevelTests(unittest.TestCase):
    def test_highest_type_wins(self):
        self.assertEqual(rb.bump_level(["fixed", "added", "breaking"]), 2)
        self.assertEqual(rb.bump_level(["fixed", "changed"]), 1)
        self.assertEqual(rb.bump_level(["security", "fixed"]), 0)
        self.assertEqual(rb.bump_level(["removed"]), 2)

    def test_unknown_or_empty_is_none(self):
        self.assertIsNone(rb.bump_level([]))
        self.assertIsNone(rb.bump_level(["misc", "notes"]))


class ApplyBumpTests(unittest.TestCase):
    def test_post_1_0(self):
        self.assertEqual(rb.apply_bump((1, 2, 3), 2), "2.0.0")
        self.assertEqual(rb.apply_bump((1, 2, 3), 1), "1.3.0")
        self.assertEqual(rb.apply_bump((1, 2, 3), 0), "1.2.4")

    def test_pre_1_0_caps_major_to_minor(self):
        # 0.x: a breaking change bumps the minor, not the major.
        self.assertEqual(rb.apply_bump((0, 1, 0), 2), "0.2.0")
        self.assertEqual(rb.apply_bump((0, 1, 0), 1), "0.2.0")
        self.assertEqual(rb.apply_bump((0, 1, 0), 0), "0.1.1")

    def test_first_release_from_zero(self):
        self.assertEqual(rb.apply_bump((0, 0, 0), 1), "0.1.0")
        self.assertEqual(rb.apply_bump((0, 0, 0), 0), "0.0.1")


class FragmentTypeTests(unittest.TestCase):
    def test_parses_types_and_ignores_meta(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "123.added.md").write_text("x", encoding="utf-8")
            (root / "+slug.fixed.md").write_text("x", encoding="utf-8")
            (root / "README.md").write_text("x", encoding="utf-8")
            (root / "_template.md.jinja").write_text("x", encoding="utf-8")
            self.assertEqual(sorted(rb.fragment_types(root)), ["added", "fixed"])


class ChangelogReadTests(unittest.TestCase):
    TEXT = (
        "# Changelog\n\n<!-- towncrier release notes start -->\n\n"
        "## [0.2.0] - 2026-07-06\n\n### Added\n\n- new thing\n\n"
        "## [0.1.0] - 2026-07-05\n\n### Added\n\n- first\n"
    )

    def test_current_version(self):
        self.assertEqual(rb.changelog_version(self.TEXT), "0.2.0")

    def test_notes_are_the_top_section_only(self):
        notes = rb.changelog_notes(self.TEXT)
        self.assertIn("new thing", notes)
        self.assertNotIn("first", notes)
        # Excludes the "## [X] - date" heading line.
        self.assertNotIn("2026-07-06", notes)
        self.assertTrue(notes.startswith("### Added"))

    def test_none_when_no_section(self):
        self.assertIsNone(rb.changelog_version("# Changelog\n\nnothing yet\n"))


if __name__ == "__main__":
    unittest.main()
