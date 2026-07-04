from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    ".ground-control.yaml",
    ".mcp.json",
    ".gc/plan-rules.md",
    "AGENTS.md",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "docs/index.md",
    "docs/repository-charter.md",
    "docs/migration-plan.md",
    "docs/scrub-policy.md",
    "docs/authoring-boundary.md",
    "docs/tracking-issues.md",
    "docs/versioning.md",
    "docs/branch-protection.md",
    "contracts/README.md",
    "schemas/README.md",
    "templates/README.md",
    "tools/README.md",
    "examples/README.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/migration_task.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml",
]

SCRUB_EXCLUDED = {Path("tests/test_repository_contract.py")}
SCRUB_TERMS = ["penumbra", "shifter"]

MIGRATION_TEMPLATE = Path(".github/ISSUE_TEMPLATE/migration_task.md")


class RepositoryContractTests(unittest.TestCase):
    def test_required_bootstrap_paths_exist(self) -> None:
        missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
        self.assertEqual([], missing)

    def test_ground_control_project_id_is_aligned(self) -> None:
        gc_config = (ROOT / ".ground-control.yaml").read_text(encoding="utf-8")
        mcp_config = (ROOT / ".mcp.json").read_text(encoding="utf-8")

        self.assertIn("project: aces-scenario-packs", gc_config)
        self.assertIn("github_repo: Brad-Edwards/aces-scenario-packs", gc_config)
        self.assertIn('"GH_REPO": "Brad-Edwards/aces-scenario-packs"', mcp_config)

    def test_bootstrap_text_is_scrubbed_of_downstream_catalog_terms(self) -> None:
        # The maintained scrub sentinel: no canonical file may carry a
        # downstream catalog term. On failure we report only the offending
        # file paths, never the matched term -- the term is private
        # vocabulary and echoing it into test output or CI logs would leak
        # exactly what the scrub policy exists to keep out (docs/scrub-policy.md).
        offenders: set[str] = set()
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if rel in SCRUB_EXCLUDED or any(part == ".git" for part in rel.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8").lower()
            except UnicodeDecodeError:
                continue
            if any(term in text for term in SCRUB_TERMS):
                offenders.add(rel.as_posix())

        self.assertEqual(set(), offenders)

    def test_migration_template_carries_source_specific_scrub_checklist(self) -> None:
        # ASP-0011 AC3: migration issues must include source-specific scrub
        # checklists. The template's Scrub Requirements section is the seam
        # that puts that checklist on every migration issue, so it must ship a
        # real checkbox list, not an empty heading.
        text = (ROOT / MIGRATION_TEMPLATE).read_text(encoding="utf-8")
        lines = text.splitlines()
        headings = [i for i, line in enumerate(lines) if line.startswith("## ")]
        section_starts = [i for i in headings if "scrub requirements" in lines[i].lower()]
        self.assertTrue(section_starts, "migration template lacks a Scrub Requirements section")
        start = section_starts[0]
        end = next((i for i in headings if i > start), len(lines))
        checklist_items = [
            line for line in lines[start + 1:end] if line.lstrip().startswith("- [ ]")
        ]
        self.assertGreaterEqual(
            len(checklist_items),
            3,
            "Scrub Requirements section must be a source-specific checklist",
        )


if __name__ == "__main__":
    unittest.main()
