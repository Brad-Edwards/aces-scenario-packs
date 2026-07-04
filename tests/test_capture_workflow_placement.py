"""Structural gates for the capture workflow placement decision (ASP-0014).

ASP-0014 records whether capture and inventory workflows move into this companion
repository, remain in ACES core, move to APTL, or split by responsibility. These
tests make that decision record machine-checkable rather than asserting prose
verbatim: the decision doc must classify capture responsibility into the three
categories the acceptance criteria call for (ACES-semantic, pack-authoring
support, APTL/runtime), inventory each responsibility by owner and placement
decision, link the ACES-side and APTL follow-ups, and carry the "no capture
asset moves before the decision is recorded" guardrail. They mirror the
structural-gate style of tests/test_authoring_tooling_ownership.py.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "docs" / "capture-workflow-placement.md"
INDEX = ROOT / "docs" / "index.md"
ADR = ROOT / "docs" / "decisions" / "adrs" / "0004-capture-workflow-placement.md"
ADR_README = ROOT / "docs" / "decisions" / "adrs" / "README.md"

REQUIRED_SECTIONS = [
    "Purpose",
    "Capture Responsibility Categories",
    "Capture Placement Decision",
    "Capture Asset Inventory",
    "ACES-Side And Downstream Follow-Ups",
    "Placement Guardrail",
]

REQUIRED_COLUMNS = [
    "Capture Responsibility",
    "Current Owner",
    "Category",
    "Placement Decision",
    "Follow-Up",
]

# AC1/AC2/AC3: the decision must identify all three responsibility categories.
REQUIRED_CATEGORIES = [
    "ACES-semantic capture responsibility",
    "Pack-authoring capture support",
    "APTL/runtime capture responsibility",
]


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


def _parse_table(body: str) -> tuple[list[str], list[list[str]]]:
    """Parse the first GitHub-flavored Markdown table in ``body``.

    Returns (header_cells, data_rows). A data row is a list of cell strings. The
    separator row (``| --- | --- |``) is skipped.
    """
    rows = [line.strip() for line in body.splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        return [], []

    def cells(line: str) -> list[str]:
        parts = [cell.strip() for cell in line.strip().strip("|").split("|")]
        return parts

    header = cells(rows[0])
    data = []
    for line in rows[2:]:  # rows[1] is the |---|---| separator
        if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        data.append(cells(line))
    return header, data


class CaptureWorkflowPlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = DECISION.read_text(encoding="utf-8") if DECISION.exists() else ""
        cls.sections = _split_sections(cls.text)

    def test_decision_doc_exists_and_is_non_empty(self) -> None:
        self.assertTrue(DECISION.exists(), f"missing capture placement decision: {DECISION}")
        self.assertGreater(len(self.text.strip()), 0, "capture placement decision is empty")

    def test_required_sections_present(self) -> None:
        missing = [name for name in REQUIRED_SECTIONS if name not in self.sections]
        self.assertEqual([], missing, f"decision missing sections: {missing}")

    def test_inventory_table_has_required_columns(self) -> None:
        header, _ = _parse_table(self.sections.get("Capture Asset Inventory", ""))
        self.assertTrue(header, "Capture Asset Inventory section has no Markdown table")
        missing = [col for col in REQUIRED_COLUMNS if col not in header]
        self.assertEqual([], missing, f"inventory table missing columns: {missing}")

    def test_every_row_has_owner_category_and_decision(self) -> None:
        # No inventory row may leave the responsibility, owner, category, or
        # placement-decision cells blank: each capture responsibility must be
        # identified and placed.
        header, data = _parse_table(self.sections.get("Capture Asset Inventory", ""))
        self.assertTrue(data, "Capture Asset Inventory table has no rows")
        index = {col: header.index(col) for col in REQUIRED_COLUMNS if col in header}
        blank: list[str] = []
        for row in data:
            for col in ("Capture Responsibility", "Current Owner", "Category", "Placement Decision"):
                value = row[index[col]] if index[col] < len(row) else ""
                if not value:
                    blank.append(f"{row[0] if row else '?'} -> {col}")
        self.assertEqual([], blank, f"inventory rows with blank required cells: {blank}")

    def test_all_three_responsibility_categories_identified(self) -> None:
        # AC1 (ACES-owned semantic capture), AC2 (pack-authoring capture
        # support), and AC3 (APTL/runtime-specific capture) must each be named
        # in the categories section.
        body = self.sections.get("Capture Responsibility Categories", "")
        missing = [name for name in REQUIRED_CATEGORIES if name not in body]
        self.assertEqual([], missing, f"categories section missing responsibilities: {missing}")

    def test_placement_decision_is_recorded(self) -> None:
        # ASP-0014 clause: decide move-in / stay-in-ACES / move-to-APTL / split.
        body = self.sections.get("Capture Placement Decision", "")
        self.assertRegex(
            body,
            r"(?is)split\b[^.]*\bby responsibility\b|remain in aces|move to aptl|move into",
            "Capture Placement Decision records no decision among the ASP-0014 options",
        )

    def test_follow_ups_reference_aces_and_aptl_issues(self) -> None:
        # AC4: ACES and APTL follow-up issues are created or linked.
        body = self.sections.get("ACES-Side And Downstream Follow-Ups", "")
        self.assertRegex(body, r"aces#\d+", "follow-up section links no ACES-side (aces#NNN) issue")
        self.assertRegex(body, r"aptl#\d+", "follow-up section links no APTL (aptl#NNN) issue")

    def test_placement_guardrail_present(self) -> None:
        # AC5: no capture workflow assets are moved before the decision is recorded.
        body = self.sections.get("Placement Guardrail", "")
        self.assertRegex(
            body,
            r"(?is)no\b[^.]*(capture|asset)[^.]*mov[^.]*before[^.]*(record|decision|owner)",
            "Placement Guardrail lacks a 'no capture asset moves before the decision is recorded' rule",
        )

    def test_adr_exists_and_is_listed(self) -> None:
        self.assertTrue(ADR.exists(), f"missing ADR: {ADR}")
        self.assertGreater(len(ADR.read_text(encoding="utf-8").strip()), 0, "ADR is empty")
        listing = ADR_README.read_text(encoding="utf-8") if ADR_README.exists() else ""
        self.assertIn(
            "0004-capture-workflow-placement.md",
            listing,
            "ADR 0004 is not listed in the ADR README",
        )

    def test_decision_is_linked_from_docs_index(self) -> None:
        listing = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        self.assertIn(
            "capture-workflow-placement.md",
            listing,
            "capture placement decision is not linked from docs/index.md",
        )


if __name__ == "__main__":
    unittest.main()
