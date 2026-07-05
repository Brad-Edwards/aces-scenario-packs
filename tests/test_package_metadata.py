"""The installed package exposes a usable version string.

Version is derived from the git tag via hatch-vcs (ADR 0006); this guards the
metadata-lookup path in ``aces_scenario_packs.__init__``.
"""

from __future__ import annotations

import unittest

import aces_scenario_packs


class VersionTests(unittest.TestCase):
    def test_version_is_non_empty_string(self):
        self.assertIsInstance(aces_scenario_packs.__version__, str)
        self.assertTrue(aces_scenario_packs.__version__.strip())


if __name__ == "__main__":
    unittest.main()
