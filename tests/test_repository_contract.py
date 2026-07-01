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
        offenders: list[str] = []
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
            for term in SCRUB_TERMS:
                if term in text:
                    offenders.append(f"{rel}: {term}")

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
