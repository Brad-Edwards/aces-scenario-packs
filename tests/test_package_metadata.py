"""The package exposes a version string.

The version is a single committed literal in ``aces_scenario_packs.__init__``
(ADR 0007), read by hatchling and bumped by ``tools/release.py``.
"""

from __future__ import annotations

import unittest

import aces_scenario_packs


class VersionTests(unittest.TestCase):
    def test_version_is_a_semver_string(self):
        self.assertIsInstance(aces_scenario_packs.__version__, str)
        self.assertRegex(aces_scenario_packs.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
