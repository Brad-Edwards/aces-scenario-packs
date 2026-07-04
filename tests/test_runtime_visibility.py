"""Tests for the runtime-visibility artifact-tier contract (issue #20).

The runtime-visibility axis classifies each declared pack artifact root by who
may see it at runtime. It is orthogonal to the ``artifact-boundary`` disposition
axis. These tests cover the published schema, its fixtures, and the two gates the
schema alone cannot express: a participant-tier leak scan and a packaging
boundary split with path containment.

All secret-shaped and restricted-tier strings here are synthetic; none are real
credentials, and none reuse any downstream scrub vocabulary.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from aces_pack_tools.schema import SchemaIndex, conformance_errors, load_json  # noqa: E402
from aces_pack_tools.validate import validate_pack, validate_record  # noqa: E402
from aces_pack_tools.visibility import (  # noqa: E402
    TIERS,
    check_visibility,
    restricted_tier_findings,
    staging_plan,
    tier_policy,
)

INDEX = ROOT / "schemas" / "index.json"
EXAMPLE = ROOT / "schemas" / "examples" / "runtime-visibility.v0.example.json"
FIXTURES = ROOT / "tests" / "fixtures" / "runtime-visibility"

# A synthetic cloud-access-key-shaped string (matches the leak scanner pattern
# without being a real key).
SYNTHETIC_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"


def _errors(findings):
    return [f for f in findings if f.severity == "error"]


class SchemaAndFixtureTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)

    def test_family_is_indexed(self):
        self.assertIn("runtime-visibility", self.index.families())

    def test_schema_id_and_version_resolve(self):
        schema = self.index.schema_for("runtime-visibility")
        self.assertEqual(schema["$id"], "urn:aces-scenario-pack:schema:runtime-visibility:v0")

    def test_valid_example_conforms(self):
        schema = self.index.schema_for("runtime-visibility")
        instance = load_json(EXAMPLE)
        self.assertEqual([], conformance_errors(instance, schema))

    def test_valid_example_passes_through_the_tool(self):
        findings = validate_record(EXAMPLE, "runtime-visibility", self.index)
        self.assertEqual([], _errors(findings))


class RecordValidationTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)

    def _write(self, tmp, obj):
        path = Path(tmp) / "runtime-visibility.json"
        path.write_text(json.dumps(obj), encoding="utf-8")
        return path

    def test_missing_required_field_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._write(tmp, {"roots": []})
            errors = _errors(validate_record(record, "runtime-visibility", self.index))
            self.assertTrue(errors)
            self.assertTrue(any("packId" in f.message for f in errors))

    def test_unknown_tier_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._write(
                tmp,
                {"packId": "p", "roots": [{"path": "docs/", "visibility": "top-secret"}]},
            )
            findings = validate_record(record, "runtime-visibility", self.index)
            errors = _errors(findings)
            self.assertTrue(any("enum" in f.message for f in errors))
            # The untrusted tier value must never be echoed into a finding.
            self.assertFalse(any("top-secret" in f.message for f in findings))

    def test_unknown_tier_violating_fixture_is_flagged(self):
        errors = _errors(
            validate_record(FIXTURES / "invalid-unknown-tier.json", "runtime-visibility", self.index)
        )
        self.assertTrue(errors)


class ContainmentTests(unittest.TestCase):
    def test_check_visibility_flags_traversal_root(self):
        record = {"packId": "p", "roots": [{"path": "../escape", "visibility": "operator-only"}]}
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            errors = _errors(findings)
            self.assertTrue(any(f.family == "runtime-visibility" for f in errors))
            self.assertTrue(all(not Path(f.path).is_absolute() for f in findings))

    def test_staging_plan_flags_traversal_root(self):
        record = {"packId": "p", "roots": [{"path": "../escape", "visibility": "oracle-only"}]}
        with tempfile.TemporaryDirectory() as tmp:
            plans, findings = staging_plan(record, Path(tmp))
            self.assertTrue(_errors(findings))
            self.assertEqual([], plans)

    def test_traversal_violating_fixture_is_flagged(self):
        record = load_json(FIXTURES / "invalid-traversal-root.json")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(_errors(check_visibility(record, Path(tmp), "runtime-visibility.json")))


class TierConflictTests(unittest.TestCase):
    def test_same_root_in_two_tiers_is_flagged(self):
        record = {
            "packId": "p",
            "roots": [
                {"path": "shared/", "visibility": "participant-visible"},
                {"path": "shared/", "visibility": "oracle-only"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            self.assertTrue(any("conflict" in f.message.lower() for f in _errors(findings)))

    def test_nested_roots_with_different_tiers_conflict(self):
        # An oracle root nested under a participant root would otherwise stage
        # into (and be scanned as) the participant tier: it must be rejected.
        record = {
            "packId": "p",
            "roots": [
                {"path": "public/", "visibility": "participant-visible"},
                {"path": "public/answers/", "visibility": "oracle-only"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            self.assertTrue(any("conflict" in f.message.lower() for f in _errors(findings)))

    def test_nested_roots_same_tier_are_allowed(self):
        record = {
            "packId": "p",
            "roots": [
                {"path": "public/", "visibility": "participant-visible"},
                {"path": "public/sub/", "visibility": "participant-visible"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            # No conflict error for same-tier nesting (missing-root warnings are ok).
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            self.assertFalse(any("conflict" in f.message.lower() for f in _errors(findings)))


class ParticipantLeakScanTests(unittest.TestCase):
    def _pack_with_root(self, tmp, root_name, filename, content):
        root_dir = Path(tmp) / root_name
        root_dir.mkdir(parents=True, exist_ok=True)
        (root_dir / filename).write_text(content, encoding="utf-8")
        return Path(tmp)

    def test_secret_in_participant_root_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._pack_with_root(tmp, "public", "readme.md", f"token = {SYNTHETIC_KEY}")
            record = {"packId": "p", "roots": [{"path": "public/", "visibility": "participant-visible"}]}
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            errors = _errors(findings)
            self.assertTrue(any(f.family == "secret" for f in errors))
            self.assertTrue(all(not Path(f.path).is_absolute() for f in findings))
            self.assertTrue(any(f.path.startswith("public/") for f in errors))

    def test_restricted_indicator_in_participant_root_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._pack_with_root(tmp, "public", "hint.md", "The flag for this challenge is elsewhere.")
            record = {"packId": "p", "roots": [{"path": "public/", "visibility": "participant-visible"}]}
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            errors = _errors(findings)
            self.assertTrue(any(f.family == "restricted-tier" for f in errors))
            # The surrounding participant text must not be echoed into the finding.
            self.assertFalse(any("challenge" in f.message for f in findings))

    def test_operator_root_is_not_leak_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            # The same restricted content in an operator-only root is legitimate.
            self._pack_with_root(tmp, "operator", "answers.md", f"The answer flag is {SYNTHETIC_KEY}")
            record = {"packId": "p", "roots": [{"path": "operator/", "visibility": "operator-only"}]}
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            self.assertEqual([], _errors(findings))

    def test_clean_participant_root_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._pack_with_root(tmp, "public", "readme.md", "A portable ACES scenario brief.")
            record = {"packId": "p", "roots": [{"path": "public/", "visibility": "participant-visible"}]}
            self.assertEqual([], _errors(check_visibility(record, Path(tmp), "runtime-visibility.json")))

    def test_missing_participant_root_warns_but_does_not_error(self):
        # A declared participant root absent from disk must not silently skip the
        # scan: it surfaces as a warning (not an error), mirroring artifact-boundary.
        with tempfile.TemporaryDirectory() as tmp:
            record = {"packId": "p", "roots": [{"path": "public/", "visibility": "participant-visible"}]}
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            self.assertEqual([], _errors(findings))
            self.assertTrue(any(f.severity == "warning" for f in findings))

    def test_caller_denylist_term_is_flagged_in_participant_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._pack_with_root(tmp, "public", "readme.md", "see the acme-secret-catalog page")
            record = {"packId": "p", "roots": [{"path": "public/", "visibility": "participant-visible"}]}
            findings = check_visibility(
                record, Path(tmp), "runtime-visibility.json", extra_terms=("acme-secret-catalog",)
            )
            errors = _errors(findings)
            self.assertTrue(any(f.family == "vocabulary" for f in errors))
            self.assertFalse(any("acme-secret-catalog" in f.message for f in findings))

    def test_single_file_participant_root_is_scanned(self):
        # A participant-visible root may point directly at a file (no trailing
        # slash), not just a directory subtree; that branch must still leak-scan.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "brief.md").write_text(f"token = {SYNTHETIC_KEY}", encoding="utf-8")
            record = {"packId": "p", "roots": [{"path": "brief.md", "visibility": "participant-visible"}]}
            findings = check_visibility(record, Path(tmp), "runtime-visibility.json")
            errors = _errors(findings)
            self.assertTrue(any(f.family == "secret" for f in errors))
            self.assertTrue(any(f.path == "brief.md" for f in errors))

    def test_restricted_tier_findings_ignores_substring_false_positive(self):
        # Word-boundary matching: "flagship" must not trip the "flag" indicator.
        self.assertEqual([], restricted_tier_findings("our flagship offering", "readme.md"))

    def test_restricted_tier_findings_reports_category_not_text(self):
        findings = restricted_tier_findings("the answer is hidden", "notes.md")
        self.assertTrue(findings)
        self.assertTrue(all(f.family == "restricted-tier" for f in findings))
        self.assertFalse(any("hidden" in f.message and "answer" not in f.message for f in findings))


class StagingPlanTests(unittest.TestCase):
    def _record(self):
        return {
            "packId": "p",
            "roots": [
                {"path": "brief/", "visibility": "participant-visible"},
                {"path": "runbook/", "visibility": "operator-only"},
                {"path": "answers/", "visibility": "oracle-only"},
                {"path": "licensed/", "visibility": "distribution-restricted"},
            ],
        }

    def test_each_tier_stages_into_its_own_release_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            plans, findings = staging_plan(self._record(), Path(tmp))
            self.assertEqual([], _errors(findings))
            by_tier = {p.tier: p for p in plans}
            for tier, plan in by_tier.items():
                self.assertTrue(plan.dest.startswith(tier_policy(tier)["release_root"] + "/"))

    def test_no_restricted_tier_stages_into_participant_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            plans, _ = staging_plan(self._record(), Path(tmp))
            participant_root = tier_policy("participant-visible")["release_root"] + "/"
            for plan in plans:
                if plan.tier != "participant-visible":
                    self.assertFalse(plan.dest.startswith(participant_root))

    def test_plan_dest_paths_are_pack_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            plans, _ = staging_plan(self._record(), Path(tmp))
            for plan in plans:
                self.assertFalse(Path(plan.dest).is_absolute())
                self.assertFalse(Path(plan.source).is_absolute())


class ValidatePackWiringTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)

    def test_validate_pack_surfaces_participant_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            public.mkdir()
            (public / "leak.md").write_text(f"key = {SYNTHETIC_KEY}", encoding="utf-8")
            (Path(tmp) / "runtime-visibility.json").write_text(
                json.dumps(
                    {"packId": "p", "roots": [{"path": "public/", "visibility": "participant-visible"}]}
                ),
                encoding="utf-8",
            )
            findings = validate_pack(Path(tmp), self.index)
            self.assertTrue(any(f.family == "secret" for f in _errors(findings)))

    def test_pack_without_visibility_record_is_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Resolve each family's fixture through the index so a version bump
            # (for example provenance v0 -> v1) does not strand this builder.
            for family in ("pack-metadata", "compatibility", "provenance", "lifecycle"):
                obj = load_json(ROOT / self.index.entry(family).fixtures[0])
                (Path(tmp) / f"{family}.json").write_text(json.dumps(obj), encoding="utf-8")
            self.assertEqual([], _errors(validate_pack(Path(tmp), self.index)))


class TierPolicyTests(unittest.TestCase):
    def test_four_tiers_defined(self):
        self.assertEqual(
            set(TIERS),
            {"participant-visible", "operator-only", "oracle-only", "distribution-restricted"},
        )

    def test_only_participant_tier_is_leak_scanned(self):
        self.assertTrue(tier_policy("participant-visible")["participant_visible"])
        for tier in ("operator-only", "oracle-only", "distribution-restricted"):
            self.assertFalse(tier_policy(tier)["participant_visible"])

    def test_unknown_tier_policy_raises(self):
        with self.assertRaises(ValueError):
            tier_policy("no-such-tier")


if __name__ == "__main__":
    unittest.main()
