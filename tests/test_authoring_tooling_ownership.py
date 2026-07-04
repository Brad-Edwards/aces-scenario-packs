"""Structural gates for the authoring/tooling ownership plan (ASP-0013).

ASP-0013 records which scenario-pack authoring helpers move into this companion
repository and which remain in ACES core or downstream consumers. These tests
make that decision record machine-checkable rather than asserting prose verbatim:
the plan must inventory each helper by source path and owner, give each a
proposed owner and a migration decision, link the ACES-side follow-ups, and carry
the "no helper moves before ownership is recorded" guardrail. They mirror the
structural-gate style of tests/test_scenario_pack_contract.py.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "authoring-tooling-ownership.md"
INDEX = ROOT / "docs" / "index.md"
ADR = ROOT / "docs" / "decisions" / "adrs" / "0003-authoring-tooling-ownership.md"
ADR_README = ROOT / "docs" / "decisions" / "adrs" / "README.md"

REQUIRED_SECTIONS = [
    "Purpose",
    "Helper Categories",
    "Helper Inventory",
    "ACES-Side And Downstream Follow-Ups",
    "Ownership Guardrail",
]

REQUIRED_COLUMNS = [
    "Source Path",
    "Current Owner",
    "Category",
    "Proposed Owner",
    "Migration Decision",
    "Follow-Up",
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


class AuthoringToolingOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = PLAN.read_text(encoding="utf-8") if PLAN.exists() else ""
        cls.sections = _split_sections(cls.text)

    def test_plan_exists_and_is_non_empty(self) -> None:
        self.assertTrue(PLAN.exists(), f"missing ownership plan: {PLAN}")
        self.assertGreater(len(self.text.strip()), 0, "ownership plan is empty")

    def test_required_sections_present(self) -> None:
        missing = [name for name in REQUIRED_SECTIONS if name not in self.sections]
        self.assertEqual([], missing, f"plan missing sections: {missing}")

    def test_inventory_table_has_required_columns(self) -> None:
        header, _ = _parse_table(self.sections.get("Helper Inventory", ""))
        self.assertTrue(header, "Helper Inventory section has no Markdown table")
        missing = [col for col in REQUIRED_COLUMNS if col not in header]
        self.assertEqual([], missing, f"inventory table missing columns: {missing}")

    def test_every_helper_row_has_source_path_owner_and_decision(self) -> None:
        # AC1 (inventoried by source path and owner) + AC2 (each helper has a
        # proposed owner and a migration decision): no inventory row may leave
        # any of those cells blank.
        header, data = _parse_table(self.sections.get("Helper Inventory", ""))
        self.assertTrue(data, "Helper Inventory table has no rows")
        index = {col: header.index(col) for col in REQUIRED_COLUMNS if col in header}
        blank: list[str] = []
        for row in data:
            for col in ("Source Path", "Current Owner", "Proposed Owner", "Migration Decision"):
                value = row[index[col]] if index[col] < len(row) else ""
                if not value:
                    blank.append(f"{row[0] if row else '?'} -> {col}")
        self.assertEqual([], blank, f"inventory rows with blank required cells: {blank}")

    def test_follow_ups_reference_aces_side_issues(self) -> None:
        # AC3: ACES-side follow-up issues are linked. The follow-up section must
        # cross-link at least one ACES-core issue (aces#NNN).
        body = self.sections.get("ACES-Side And Downstream Follow-Ups", "")
        self.assertRegex(
            body,
            r"aces#\d+",
            "follow-up section links no ACES-side (aces#NNN) issue",
        )

    def test_ownership_guardrail_present(self) -> None:
        # AC4: no helper is moved before ownership is recorded.
        body = self.sections.get("Ownership Guardrail", "")
        self.assertRegex(
            body,
            r"(?is)no\b[^.]*helper[^.]*mov[^.]*before[^.]*(record|owner)",
            "Ownership Guardrail lacks a 'no helper moves before ownership recorded' rule",
        )

    def test_adr_exists_and_is_listed(self) -> None:
        self.assertTrue(ADR.exists(), f"missing ADR: {ADR}")
        self.assertGreater(len(ADR.read_text(encoding="utf-8").strip()), 0, "ADR is empty")
        listing = ADR_README.read_text(encoding="utf-8") if ADR_README.exists() else ""
        self.assertIn(
            "0003-authoring-tooling-ownership.md",
            listing,
            "ADR 0003 is not listed in the ADR README",
        )

    def test_plan_is_linked_from_docs_index(self) -> None:
        listing = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        self.assertIn(
            "authoring-tooling-ownership.md",
            listing,
            "ownership plan is not linked from docs/index.md",
        )


if __name__ == "__main__":
    unittest.main()
