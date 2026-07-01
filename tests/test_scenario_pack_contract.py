"""Structural gates for the ACES scenario-pack contract (ASP-0002).

These tests make the contract's normative claims machine-checkable rather than
asserting prose verbatim: required sections must exist, every optional layer
must declare its applicability and validation, the lifecycle vocabulary must
stay within the ACES-native pack-maturity set (so downstream catalog statuses
cannot leak in), and every open question must point at a follow-up issue.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "scenario-pack-contract.md"

REQUIRED_SECTIONS = [
    "Terminology",
    "Minimum Pack Shape",
    "Optional Layers",
    "Lifecycle States",
    "Compatibility Boundaries",
    "Open Questions",
]

# ACES-native pack maturity / publication vocabulary. The contract's canonical
# lifecycle set MUST be a subset of this; any downstream catalog workflow status
# (e.g. a challenge-platform "solved"/"in-play"/"retired" status) is rejected by
# construction because it is not in this set.
ALLOWED_LIFECYCLE_STATES = {
    "Draft",
    "Candidate",
    "Published",
    "Deprecated",
    "Withdrawn",
}


def _split_sections(text: str) -> dict[str, str]:
    """Return a map of level-2 heading title -> section body (up to the next ##)."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^##\s+(?P<title>.+?)\s*$", line)
        if match:
            if current is not None:
                sections[current] = "\n".join(buf)
            current = match.group("title")
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


class ScenarioPackContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CONTRACT.read_text(encoding="utf-8") if CONTRACT.exists() else ""
        cls.sections = _split_sections(cls.text)

    def test_contract_exists_and_is_non_empty(self) -> None:
        self.assertTrue(CONTRACT.exists(), f"missing contract: {CONTRACT}")
        self.assertGreater(len(self.text.strip()), 0, "contract file is empty")

    def test_required_sections_present(self) -> None:
        missing = [name for name in REQUIRED_SECTIONS if name not in self.sections]
        self.assertEqual([], missing, f"contract missing sections: {missing}")

    def test_optional_layers_are_explicit_and_testable(self) -> None:
        body = self.sections.get("Optional Layers", "")
        layers = re.findall(
            r"^###\s+Layer:\s*(?P<name>.+?)\s*$(?P<body>.*?)(?=^###\s|\Z)",
            body,
            flags=re.MULTILINE | re.DOTALL,
        )
        self.assertTrue(layers, "Optional Layers section declares no '### Layer:' entries")
        for name, layer_body in layers:
            with self.subTest(layer=name):
                self.assertRegex(
                    layer_body,
                    r"(?mi)^\s*(?:[-*]\s+)?Applicability:\s*\S",
                    f"layer '{name}' has no Applicability: line",
                )
                self.assertRegex(
                    layer_body,
                    r"(?mi)^\s*(?:[-*]\s+)?Validation:\s*\S",
                    f"layer '{name}' has no Validation: line",
                )

    def test_lifecycle_states_are_aces_native(self) -> None:
        body = self.sections.get("Lifecycle States", "")
        match = re.search(r"(?mi)^\s*Canonical states:\s*(?P<list>.+?)\s*$", body)
        self.assertIsNotNone(
            match, "Lifecycle States section has no 'Canonical states:' enumeration"
        )
        declared = {
            state.strip()
            for state in re.split(r"[,.]", match.group("list"))
            if state.strip()
        }
        self.assertTrue(declared, "no lifecycle states enumerated")
        leaked = declared - ALLOWED_LIFECYCLE_STATES
        self.assertEqual(
            set(), leaked, f"lifecycle states outside the ACES-native set: {sorted(leaked)}"
        )

    def test_open_questions_reference_follow_up_issues(self) -> None:
        body = self.sections.get("Open Questions", "")
        # Group each bullet with its wrapped continuation lines so an issue
        # reference on a continuation line still counts.
        bullets: list[str] = []
        for line in body.splitlines():
            if line.lstrip().startswith("- "):
                bullets.append(line)
            elif bullets and line.strip():
                bullets[-1] += " " + line.strip()
        self.assertTrue(bullets, "Open Questions section has no bullet entries")
        unreferenced = [b for b in bullets if not re.search(r"#\d+", b)]
        self.assertEqual(
            [], unreferenced, f"open questions without a follow-up issue link: {unreferenced}"
        )


if __name__ == "__main__":
    unittest.main()
