"""Tests for the contract-v1 provenance ledger (issue #21).

The v1 provenance ledger brings the schema to parity with the four-part
incumbent pack convention: a first-class ``sources[]`` ledger, a per-artifact
distribution class, an all-true content-safety attestation, and a per-gate
publication-review checklist, plus path-contained consumer overlays. These tests
cover the published schema, its fixtures, and the gates the schema alone cannot
express (attestation all-true, blocked-review rejection, attribution
completeness, source-reference integrity, and overlay containment / non-overlap).

All secret-shaped and vocabulary strings here are synthetic; none are real
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

from aces_pack_tools.schema import (  # noqa: E402
    SchemaIndex,
    conformance_errors,
    load_json,
    normalize_subtree,
    subtrees_overlap,
)
from aces_pack_tools.provenance import check_provenance  # noqa: E402
from aces_pack_tools.validate import validate_pack  # noqa: E402

INDEX = ROOT / "schemas" / "index.json"
EXAMPLE = ROOT / "schemas" / "examples" / "provenance.v1.example.json"
FIXTURES = ROOT / "tests" / "fixtures" / "provenance"
EXAMPLES = ROOT / "schemas" / "examples"


def _errors(findings):
    return [f for f in findings if f.severity == "error"]


def _valid_record():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class SchemaAndFixtureTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)

    def test_family_is_indexed(self):
        self.assertIn("provenance", self.index.families())

    def test_schema_id_and_version_advanced_to_v1(self):
        schema = self.index.schema_for("provenance")
        self.assertEqual(schema["$id"], "urn:aces-scenario-pack:schema:provenance:v1")

    def test_v0_schema_is_gone(self):
        self.assertFalse((ROOT / "schemas" / "provenance.v0.schema.json").exists())
        self.assertFalse((EXAMPLES / "provenance.v0.example.json").exists())

    def test_valid_example_conforms(self):
        schema = self.index.schema_for("provenance")
        self.assertEqual([], conformance_errors(_valid_record(), schema))

    def test_valid_example_passes_gates_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_provenance(_valid_record(), Path(tmp), "provenance.json")
            self.assertEqual([], _errors(findings))

    def test_distribution_classes_are_the_six_incumbent_classes(self):
        schema = self.index.schema_for("provenance")
        enum = schema["properties"]["artifacts"]["items"]["properties"]["distributionClass"]["enum"]
        self.assertEqual(
            set(enum),
            {"open", "redistributable", "internal-only", "commercial-only", "generated", "consumer-specific"},
        )


class ConformanceTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)
        self.schema = self.index.schema_for("provenance")

    def test_missing_required_ledger_parts_are_flagged(self):
        for missing in ("sources", "artifacts", "contentSafety", "publicationReview"):
            record = _valid_record()
            del record[missing]
            with self.subTest(missing=missing):
                self.assertTrue(conformance_errors(record, self.schema))

    def test_missing_attestation_gate_is_flagged_by_schema(self):
        record = _valid_record()
        del record["contentSafety"]["noRealCredentials"]
        self.assertTrue(conformance_errors(record, self.schema))

    def test_unknown_review_status_is_flagged_by_schema(self):
        record = _valid_record()
        record["publicationReview"]["licensing"] = "waived"
        errors = conformance_errors(record, self.schema)
        self.assertTrue(any("enum" in e for e in errors))
        self.assertFalse(any("waived" in e for e in errors))


class ContentSafetyGateTests(unittest.TestCase):
    def _record_with_gate(self, gate, value):
        record = _valid_record()
        record["contentSafety"][gate] = value
        return record

    def test_false_attestation_gate_is_flagged(self):
        for gate in (
            "noRealMalware",
            "noRealThirdPartyTargets",
            "noRealCredentials",
            "noSensitiveData",
            "offensiveToolingBoundary",
        ):
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as tmp:
                findings = check_provenance(self._record_with_gate(gate, False), Path(tmp), "provenance.json")
                errors = _errors(findings)
                self.assertTrue(any(f.family == "content-safety" for f in errors))

    def test_all_true_attestation_has_no_content_safety_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_provenance(_valid_record(), Path(tmp), "provenance.json")
            self.assertFalse(any(f.family == "content-safety" for f in findings))

    def test_failing_attestation_surfaces_through_validate_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._record_with_gate("noRealCredentials", False)
            _write_min_pack(tmp, provenance=record)
            findings = validate_pack(Path(tmp), SchemaIndex(INDEX))
            self.assertTrue(any(f.family == "content-safety" for f in _errors(findings)))


class PublicationReviewGateTests(unittest.TestCase):
    def test_blocked_gate_is_flagged(self):
        for gate in ("licensing", "attribution", "sensitiveData", "offensiveTooling"):
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as tmp:
                record = _valid_record()
                record["publicationReview"][gate] = "blocked"
                errors = _errors(check_provenance(record, Path(tmp), "provenance.json"))
                self.assertTrue(any(f.family == "publication-review" for f in errors))

    def test_pending_gate_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["publicationReview"]["attribution"] = "pending"
            findings = check_provenance(record, Path(tmp), "provenance.json")
            self.assertFalse(any(f.family == "publication-review" for f in _errors(findings)))

    def test_blocked_review_is_distinct_from_content_safety(self):
        # A blocked review gate must not be reported as a content-safety failure.
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["publicationReview"]["sensitiveData"] = "blocked"
            findings = check_provenance(record, Path(tmp), "provenance.json")
            self.assertTrue(any(f.family == "publication-review" for f in _errors(findings)))
            self.assertFalse(any(f.family == "content-safety" for f in findings))


class AttributionGateTests(unittest.TestCase):
    def test_missing_attribution_text_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["sources"].append(
                {"id": "needs-credit", "kind": "dataset", "license": "CC-BY-4.0",
                 "usage": "example", "attributionRequired": True}
            )
            errors = _errors(check_provenance(record, Path(tmp), "provenance.json"))
            self.assertTrue(any(f.family == "attribution" for f in errors))

    def test_empty_attribution_text_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["sources"][1]["attributionText"] = "   "
            errors = _errors(check_provenance(record, Path(tmp), "provenance.json"))
            self.assertTrue(any(f.family == "attribution" for f in errors))

    def test_attribution_text_is_not_echoed(self):
        # The attribution gate can only fire on a source whose text is blank, so a
        # genuinely-failing source cannot simultaneously carry a non-blank secret in
        # attributionText. Plant the sensitive value on the field the gate reads for
        # the failing source itself — its id — and confirm the finding it produces
        # does not echo it (mirrors test_dangling_source_id_is_not_echoed).
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            secret_id = "SENSITIVE-CREDIT-STRING"
            record["sources"].append(
                {"id": secret_id, "kind": "dataset", "license": "CC-BY-4.0", "usage": "u",
                 "attributionRequired": True, "attributionText": "  "}
            )
            findings = check_provenance(record, Path(tmp), "provenance.json")
            # The failing source must actually be flagged, so the redaction
            # assertion below is exercised rather than vacuously true.
            self.assertTrue(any(f.family == "attribution" for f in _errors(findings)))
            self.assertFalse(any(secret_id in f.message for f in findings))


class SourceReferenceGateTests(unittest.TestCase):
    def test_dangling_source_reference_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["artifacts"][0]["sources"] = ["no-such-source"]
            errors = _errors(check_provenance(record, Path(tmp), "provenance.json"))
            self.assertTrue(any(f.family == "source-reference" for f in errors))

    def test_dangling_source_id_is_not_echoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["artifacts"][0]["sources"] = ["leaky-private-id"]
            findings = check_provenance(record, Path(tmp), "provenance.json")
            self.assertFalse(any("leaky-private-id" in f.message for f in findings))

    def test_resolving_reference_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["artifacts"][0]["sources"] = ["aces-contract"]
            findings = check_provenance(record, Path(tmp), "provenance.json")
            self.assertFalse(any(f.family == "source-reference" for f in _errors(findings)))


class OverlayGateTests(unittest.TestCase):
    def test_overlay_overlapping_base_root_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["artifacts"] = [
                {"path": "scenarios/", "distributionClass": "open"},
                {"path": "scenarios/consumer/", "distributionClass": "consumer-specific"},
            ]
            errors = _errors(check_provenance(record, Path(tmp), "provenance.json"))
            self.assertTrue(any(f.family == "overlay" for f in errors))

    def test_overlay_equal_to_base_root_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["artifacts"] = [
                {"path": "shared/", "distributionClass": "open"},
                {"path": "shared/", "distributionClass": "consumer-specific"},
            ]
            errors = _errors(check_provenance(record, Path(tmp), "provenance.json"))
            self.assertTrue(any(f.family == "overlay" for f in errors))

    def test_overlay_traversal_root_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["artifacts"] = [
                {"path": "scenarios/", "distributionClass": "open"},
                {"path": "../escape/", "distributionClass": "consumer-specific"},
            ]
            findings = check_provenance(record, Path(tmp), "provenance.json")
            self.assertTrue(_errors(findings))
            self.assertTrue(all(not Path(f.path).is_absolute() for f in findings))

    def test_disjoint_overlay_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["artifacts"] = [
                {"path": "scenarios/", "distributionClass": "open"},
                {"path": "overlays/acme/", "distributionClass": "consumer-specific"},
            ]
            findings = check_provenance(record, Path(tmp), "provenance.json")
            self.assertFalse(any(f.family == "overlay" for f in _errors(findings)))

    def test_base_roots_may_nest(self):
        # Distribution class over base roots is a claim, not a packaging split;
        # base roots nesting is not the overlay gate's concern.
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["artifacts"] = [
                {"path": "pack/", "distributionClass": "open"},
                {"path": "pack/generated/", "distributionClass": "generated"},
            ]
            findings = check_provenance(record, Path(tmp), "provenance.json")
            self.assertFalse(any(f.family == "overlay" for f in _errors(findings)))


class SanitizationTests(unittest.TestCase):
    def test_findings_are_pack_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = _valid_record()
            record["contentSafety"]["noRealMalware"] = False
            record["publicationReview"]["licensing"] = "blocked"
            record["artifacts"].append({"path": "../x/", "distributionClass": "consumer-specific"})
            findings = check_provenance(record, Path(tmp), "provenance.json")
            self.assertTrue(findings)
            self.assertTrue(all(not Path(f.path).is_absolute() for f in findings))


class FixtureTests(unittest.TestCase):
    def _flag(self, name):
        with tempfile.TemporaryDirectory() as tmp:
            return _errors(check_provenance(load_json(FIXTURES / name), Path(tmp), name))

    def test_failing_attestation_fixture(self):
        self.assertTrue(any(f.family == "content-safety" for f in self._flag("invalid-attestation.json")))

    def test_blocked_review_fixture(self):
        self.assertTrue(any(f.family == "publication-review" for f in self._flag("invalid-blocked-review.json")))

    def test_overlay_overlap_fixture(self):
        self.assertTrue(any(f.family == "overlay" for f in self._flag("invalid-overlay-overlap.json")))

    def test_overlay_traversal_fixture(self):
        self.assertTrue(self._flag("invalid-overlay-traversal.json"))

    def test_missing_attribution_fixture(self):
        self.assertTrue(any(f.family == "attribution" for f in self._flag("invalid-missing-attribution.json")))

    def test_dangling_source_fixture(self):
        self.assertTrue(any(f.family == "source-reference" for f in self._flag("invalid-dangling-source.json")))


class SharedSubtreeHelperTests(unittest.TestCase):
    def test_normalize_strips_and_splits(self):
        self.assertEqual(normalize_subtree("/a/b/"), ("a", "b"))
        self.assertEqual(normalize_subtree("a/./b"), ("a", "b"))
        self.assertEqual(normalize_subtree(""), ())

    def test_overlap_is_ancestor_descendant_or_equal(self):
        self.assertTrue(subtrees_overlap(("a",), ("a", "b")))
        self.assertTrue(subtrees_overlap(("a", "b"), ("a",)))
        self.assertTrue(subtrees_overlap(("a",), ("a",)))
        self.assertFalse(subtrees_overlap(("a",), ("b",)))
        self.assertFalse(subtrees_overlap(("a", "b"), ("a", "c")))


def _write_min_pack(tmp, provenance):
    """Write a minimum-shape pack into ``tmp`` with the given provenance record."""
    for family in ("pack-metadata", "compatibility", "lifecycle"):
        obj = load_json(EXAMPLES / f"{family}.v0.example.json")
        (Path(tmp) / f"{family}.json").write_text(json.dumps(obj), encoding="utf-8")
    (Path(tmp) / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
