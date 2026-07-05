"""Tests for the repository-side PR title guard (tools/check_pr_title.py).

The CI workflow and these tests call the same ``validate_pr_title``, so the
policy can't drift between the workflow YAML and local enforcement (ADR 0006).
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_GUARD = Path(__file__).resolve().parents[1] / "tools" / "check_pr_title.py"
_spec = importlib.util.spec_from_file_location("check_pr_title", _GUARD)
guard = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
# Register before exec so @dataclass annotation resolution can find the module.
sys.modules[_spec.name] = guard
_spec.loader.exec_module(guard)


def _rules(title: str) -> set[str]:
    return {v.rule_id for v in guard.validate_pr_title(title)}


class PrTitleGuardTests(unittest.TestCase):
    def test_valid_conventional_titles_pass(self):
        for title in (
            "feat: add the widget",
            "fix(parser): handle empty input",
            "docs: clarify the contract",
            "feat!: drop the legacy field",
            "chore: bump dev deps",
        ):
            with self.subTest(title=title):
                self.assertEqual(guard.validate_pr_title(title), [])

    def test_branded_prefixes_rejected(self):
        for title in ("[claude] feat: x", "[Codex] fix: y", "  [openai] docs: z"):
            with self.subTest(title=title):
                self.assertIn(guard.RULE_AGENT_BRAND, _rules(title))

    def test_tool_name_later_in_subject_is_allowed(self):
        self.assertEqual(guard.validate_pr_title("docs: document the claude adapter"), [])

    def test_non_conventional_rejected(self):
        for title in ("add the widget", "Fix: thing", "feat add thing", "wip: stuff"):
            with self.subTest(title=title):
                self.assertIn(guard.RULE_CONVENTIONAL, _rules(title))

    def test_uppercase_subject_rejected(self):
        self.assertIn(guard.RULE_SUBJECT_LOWERCASE, _rules("feat: Add the widget"))

    def test_empty_rejected(self):
        self.assertIn(guard.RULE_EMPTY, _rules("   "))

    def test_main_accepts_via_title_arg(self):
        self.assertEqual(guard.main(["--title", "feat: ok"]), 0)

    def test_main_rejects_via_title_arg(self):
        self.assertEqual(guard.main(["--title", "[claude] nope"]), 1)


if __name__ == "__main__":
    unittest.main()
