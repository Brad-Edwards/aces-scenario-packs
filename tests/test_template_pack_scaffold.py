"""Structural gates for the template scenario-pack scaffold (ASP-0003).

The scaffold under templates/scenario-pack/ must demonstrate the contract's
minimum pack shape with explicit, machine-searchable placeholder markers, stay
self-contained, and declare every optional layer the contract defines. These
tests enforce those claims and keep the template aligned with
contracts/scenario-pack-contract.md rather than asserting prose verbatim.
"""

from pathlib import Path
import re
import unittest

from tests.test_scenario_pack_contract import (
    ALLOWED_LIFECYCLE_STATES,
    CONTRACT,
    _split_sections,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates" / "scenario-pack"
MANIFEST = TEMPLATE_DIR / "pack-manifest.md"
PROVENANCE = TEMPLATE_DIR / "provenance.md"
SCENARIO = TEMPLATE_DIR / "scenarios" / "example-scenario.md"
README = TEMPLATE_DIR / "README.md"

REQUIRED_FILES = [README, MANIFEST, PROVENANCE, SCENARIO]

REQUIRED_MANIFEST_SECTIONS = [
    "Identity",
    "ACES SDL Contract",
    "Lifecycle",
    "Provenance and Compatibility",
    "Scenarios",
    "Optional Layers",
]

PLACEHOLDER_MARKER = "PLACEHOLDER:"


def _contract_layer_names() -> list[str]:
    body = _split_sections(CONTRACT.read_text(encoding="utf-8")).get("Optional Layers", "")
    return re.findall(r"^###\s+Layer:\s*(?P<name>.+?)\s*$", body, flags=re.MULTILINE)


class TemplatePackScaffoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest_text = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        cls.manifest_sections = _split_sections(cls.manifest_text)

    def test_scaffold_files_exist(self) -> None:
        missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.exists()]
        self.assertEqual([], missing, f"template scaffold missing files: {missing}")

    def test_manifest_declares_minimum_shape(self) -> None:
        missing = [s for s in REQUIRED_MANIFEST_SECTIONS if s not in self.manifest_sections]
        self.assertEqual([], missing, f"manifest missing sections: {missing}")

    def test_placeholder_markers_present(self) -> None:
        for path in (MANIFEST, PROVENANCE, SCENARIO):
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertTrue(path.exists(), f"missing {path}")
                self.assertIn(
                    PLACEHOLDER_MARKER,
                    path.read_text(encoding="utf-8"),
                    f"{path.name} has no '{PLACEHOLDER_MARKER}' markers",
                )

    def test_lifecycle_state_is_aces_native(self) -> None:
        body = self.manifest_sections.get("Lifecycle", "")
        match = re.search(r"(?mi)^\s*(?:[-*]\s+)?Lifecycle state:\s*(?P<state>\S+)", body)
        self.assertIsNotNone(match, "Lifecycle section has no 'Lifecycle state:' declaration")
        state = match.group("state").strip()
        self.assertIn(
            state,
            ALLOWED_LIFECYCLE_STATES,
            f"template lifecycle state '{state}' is not in the ACES-native set",
        )

    def test_optional_layers_declared_explicitly(self) -> None:
        body = self.manifest_sections.get("Optional Layers", "")
        layer_names = _contract_layer_names()
        self.assertTrue(layer_names, "contract declares no optional layers to mirror")
        for name in layer_names:
            with self.subTest(layer=name):
                line = next(
                    (ln for ln in body.splitlines() if name in ln), None
                )
                self.assertIsNotNone(line, f"manifest does not declare optional layer '{name}'")
                self.assertRegex(
                    line,
                    r"(?i)\b(?:not-)?provided\b",
                    f"layer '{name}' lacks an explicit provided/not-provided declaration",
                )

    def test_scaffold_is_self_contained(self) -> None:
        refs = re.findall(r"[\w./-]+\.md", self.manifest_text)
        internal = [r for r in refs if not r.startswith(("http", "../")) and "pack-manifest" not in r]
        self.assertTrue(internal, "manifest references no internal template files")
        for ref in internal:
            with self.subTest(ref=ref):
                self.assertTrue(
                    (TEMPLATE_DIR / ref).exists(),
                    f"manifest references '{ref}' which is not inside the template",
                )


if __name__ == "__main__":
    unittest.main()
