"""Package metadata and the reviewed ACES dependency seam.

The project version is owned by release-please in ``pyproject.toml``; the
package derives ``__version__`` from installed metadata (ADR 0008).
"""

from __future__ import annotations

import importlib.util
import pathlib
import tomllib
import unittest

import aces_scenario_packs


class VersionTests(unittest.TestCase):
    def test_version_is_a_semver_string(self):
        self.assertIsInstance(aces_scenario_packs.__version__, str)
        self.assertRegex(aces_scenario_packs.__version__, r"^\d+\.\d+\.\d+$")


class AcesDependencyTests(unittest.TestCase):
    def test_aces_sdl_is_exactly_pinned_to_0_21_0(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        with (root / "pyproject.toml").open("rb") as handle:
            dependencies = tomllib.load(handle)["project"]["dependencies"]

        self.assertIn("aces-sdl==0.21.0", dependencies)
        self.assertFalse(any(dep.startswith("aces-sdl") and dep != "aces-sdl==0.21.0"
                             for dep in dependencies))

    def test_bespoke_oracle_package_surface_is_absent(self):
        package_root = pathlib.Path(aces_scenario_packs.__file__).resolve().parent

        self.assertFalse((package_root / "oracle_model.py").exists())
        self.assertFalse((package_root / "resources" / "oracle").exists())
        self.assertIsNone(importlib.util.find_spec("aces_scenario_packs.oracle_model"))


if __name__ == "__main__":
    unittest.main()
