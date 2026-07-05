"""The installed package exposes a usable version string.

Version is derived from the git tag via hatch-vcs (ADR 0006); these guard the
metadata-lookup path in ``aces_scenario_packs.__init__``, including the
source-tree fallback when installed metadata is absent.
"""

from __future__ import annotations

import importlib
from importlib import metadata
from unittest import mock

import unittest

import aces_scenario_packs


class VersionTests(unittest.TestCase):
    def test_version_is_non_empty_string(self):
        self.assertIsInstance(aces_scenario_packs.__version__, str)
        self.assertTrue(aces_scenario_packs.__version__.strip())

    def test_falls_back_to_zero_when_metadata_missing(self):
        with mock.patch.object(
            metadata, "version", side_effect=metadata.PackageNotFoundError
        ):
            reloaded = importlib.reload(aces_scenario_packs)
            self.assertEqual(reloaded.__version__, "0.0.0")
        # Restore the real, metadata-derived version for other tests.
        importlib.reload(aces_scenario_packs)


if __name__ == "__main__":
    unittest.main()
