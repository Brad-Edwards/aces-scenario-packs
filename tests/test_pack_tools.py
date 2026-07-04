"""Tests for the ASP-0005 scenario-pack validation and release tooling.

These exercise the static, offline ``aces_pack_tools`` package end to end: the
schema-index loader and path guard, record/pack validation, the runtime-profile
portability gate, the leak scanner, the release-record check, and the argparse
CLI contract the consumer CI example depends on. The package is imported the way
an external adopter would run it — as the top-level ``aces_pack_tools`` package
with ``tools/`` on the path — so the tests double as a relocation smoke test.

All secret-shaped and denylisted strings here are synthetic; none are real
credentials, and none reuse the repository's downstream scrub terms.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from aces_pack_tools.leak import scan_pack, scan_text
from aces_pack_tools.model import Finding
from aces_pack_tools.release import check_release
from aces_pack_tools.schema import SchemaIndex, resolve_within_root
from aces_pack_tools.validate import check_profile, validate_pack, validate_record

INDEX = ROOT / "schemas" / "index.json"
EXAMPLES = ROOT / "schemas" / "examples"

# Repo example fixtures keyed by family (named "<family>.<contract-version>.example.json";
# provenance advanced to the v1 contract line, the rest are still v0).
FAMILY_EXAMPLE = {
    "pack-metadata": EXAMPLES / "pack-metadata.v0.example.json",
    "compatibility": EXAMPLES / "compatibility.v0.example.json",
    "provenance": EXAMPLES / "provenance.v1.example.json",
    "artifact-boundary": EXAMPLES / "artifact-boundary.v0.example.json",
    "runtime-visibility": EXAMPLES / "runtime-visibility.v0.example.json",
    "runtime-profile": EXAMPLES / "runtime-profile.v0.example.json",
    "delivery-bundle": EXAMPLES / "delivery-bundle.v0.example.json",
    "lifecycle": EXAMPLES / "lifecycle.v0.example.json",
    "validation": EXAMPLES / "validation.v0.example.json",
    "release": EXAMPLES / "release.v0.example.json",
}


def _errors(findings):
    return [f for f in findings if f.severity == "error"]


class SchemaIndexTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)

    def test_loads_every_published_family(self):
        for family in FAMILY_EXAMPLE:
            self.assertIn(family, self.index.families())

    def test_schema_for_returns_loaded_document(self):
        schema = self.index.schema_for("release")
        self.assertEqual(schema["$id"], "urn:aces-scenario-pack:schema:release:v0")

    def test_unknown_family_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.index.schema_for("no-such-family")

    def test_repo_fixtures_conform_through_the_tool(self):
        # Dogfood: every published fixture must validate through the same code
        # path the tool ships, tying the tool to schemas/index.json.
        for family, fixture in FAMILY_EXAMPLE.items():
            with self.subTest(family=family):
                findings = validate_record(fixture, family, self.index)
                self.assertEqual([], _errors(findings))


class RecordValidationTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)

    def _write(self, tmp, name, obj):
        path = Path(tmp) / name
        path.write_text(json.dumps(obj), encoding="utf-8")
        return path

    def test_missing_required_field_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._write(tmp, "validation.json", {"checks": []})
            findings = validate_record(record, "validation", self.index)
            errors = _errors(findings)
            self.assertTrue(errors)
            self.assertEqual("schema", errors[0].check)
            self.assertEqual("validation", errors[0].family)
            self.assertIn("packId", errors[0].message)

    def test_enum_violation_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._write(
                tmp,
                "validation.json",
                {"packId": "p", "checks": [{"name": "n", "kind": "structural", "result": "maybe"}]},
            )
            findings = validate_record(record, "validation", self.index)
            errors = _errors(findings)
            self.assertTrue(errors)
            self.assertTrue(any("enum" in f.message for f in errors))
            # The untrusted instance value must never be echoed into a finding.
            self.assertFalse(any("maybe" in f.message for f in findings))

    def test_unknown_family_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._write(tmp, "x.json", {"packId": "p"})
            with self.assertRaises(ValueError):
                validate_record(record, "not-a-family", self.index)

    def test_finding_never_carries_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._write(tmp, "validation.json", {"checks": []})
            findings = validate_record(record, "validation", self.index)
            for f in findings:
                self.assertFalse(Path(f.path).is_absolute(), f.path)


class ProfileGateTests(unittest.TestCase):
    def test_portable_profile_passes(self):
        record = json.loads(FAMILY_EXAMPLE["runtime-profile"].read_text(encoding="utf-8"))
        self.assertEqual([], _errors(check_profile(record, "runtime-profile.json")))

    def test_private_host_requirement_is_flagged(self):
        record = {
            "packId": "p",
            "profile": {"name": "x", "portable": True, "requires": ["https://internal.example/api"]},
        }
        findings = check_profile(record, "runtime-profile.json")
        self.assertTrue(_errors(findings))
        self.assertEqual("profile", findings[0].check)

    def test_ip_address_requirement_is_flagged(self):
        record = {
            "packId": "p",
            "profile": {"name": "x", "portable": True, "requires": ["10.0.0.5:8080"]},
        }
        self.assertTrue(_errors(check_profile(record, "runtime-profile.json")))


class LeakScanTests(unittest.TestCase):
    def test_detects_synthetic_private_key_block(self):
        text = "-----BEGIN PRIVATE KEY-----\nAAAAsynthetic\n-----END PRIVATE KEY-----\n"
        findings = scan_text(text, "notes.md", ())
        self.assertTrue(_errors(findings))
        # The finding must not echo the surrounding material verbatim.
        self.assertNotIn("synthetic", findings[0].message)

    def test_detects_synthetic_cloud_access_key(self):
        text = "aws_key = AKIA" + "ABCDEFGHIJKLMNOP"
        self.assertTrue(_errors(scan_text(text, "config.txt", ())))

    def test_detects_denylisted_vocabulary_term(self):
        findings = scan_text("see the acme-internal-catalog runbook", "readme.md", ("acme-internal-catalog",))
        errors = _errors(findings)
        self.assertTrue(errors)
        self.assertTrue(any(f.family == "vocabulary" for f in errors))
        # The denylisted term itself is private vocabulary and must not be echoed.
        self.assertFalse(any("acme-internal-catalog" in f.message for f in findings))

    def test_scan_pack_rejects_symlink_escaping_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret = Path(tmp) / "secret.txt"
            secret.write_text("token = AKIA" + "ABCDEFGHIJKLMNOP", encoding="utf-8")
            pack = Path(tmp) / "pack"
            pack.mkdir()
            link = pack / "link.txt"
            try:
                link.symlink_to(secret)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unsupported on this platform")
            findings = scan_pack(pack, denylist_terms=())
            # The escape is reported, and the out-of-root secret is NOT scanned.
            self.assertTrue(any(f.family == "path" for f in findings))
            self.assertFalse(any(f.family == "secret" for f in findings))
            self.assertTrue(all(not Path(f.path).is_absolute() for f in findings))

    def test_clean_text_has_no_findings(self):
        self.assertEqual([], scan_text("a portable ACES scenario pack", "readme.md", ("acme-internal-catalog",)))

    def test_scan_pack_walks_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.md").write_text("clean", encoding="utf-8")
            (Path(tmp) / "b.txt").write_text("token = AKIA" + "ABCDEFGHIJKLMNOP", encoding="utf-8")
            findings = scan_pack(Path(tmp), denylist_terms=())
            self.assertTrue(_errors(findings))
            self.assertTrue(all(not Path(f.path).is_absolute() for f in findings))


class ReleaseCheckTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)

    def _write(self, tmp, obj):
        path = Path(tmp) / "release.json"
        path.write_text(json.dumps(obj), encoding="utf-8")
        return path

    def test_repo_release_example_passes(self):
        findings = check_release(FAMILY_EXAMPLE["release"], self.index)
        self.assertEqual([], _errors(findings))

    def test_unknown_schema_family_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._write(
                tmp,
                {
                    "packId": "p",
                    "releaseVersion": "0.1.0",
                    "schemaVersions": [{"family": "bogus", "version": "0.1.0"}],
                    "compatibilityImpact": {"level": "additive"},
                },
            )
            findings = check_release(record, self.index)
            errors = _errors(findings)
            self.assertTrue(any("unknown schema family" in f.message for f in errors))
            # The untrusted family name from the record must not be echoed.
            self.assertFalse(any("bogus" in f.message for f in findings))

    def test_schema_version_mismatch_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._write(
                tmp,
                {
                    "packId": "p",
                    "releaseVersion": "0.1.0",
                    "schemaVersions": [{"family": "pack-metadata", "version": "9.9.9"}],
                    "compatibilityImpact": {"level": "additive"},
                },
            )
            self.assertTrue(_errors(check_release(record, self.index)))


class PathSafetyTests(unittest.TestCase):
    def test_resolve_within_root_allows_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolve_within_root(Path(tmp), "sub/file.json")  # must not raise

    def test_resolve_within_root_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                resolve_within_root(Path(tmp), "../../etc/passwd")


class PackValidationTests(unittest.TestCase):
    def setUp(self):
        self.index = SchemaIndex(INDEX)

    def _pack(self, tmp, families):
        for family in families:
            obj = json.loads(FAMILY_EXAMPLE[family].read_text(encoding="utf-8"))
            (Path(tmp) / f"{family}.json").write_text(json.dumps(obj), encoding="utf-8")

    def test_valid_pack_directory_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            # A minimum-shape pack carries every required record.
            self._pack(tmp, ["pack-metadata", "compatibility", "provenance", "lifecycle"])
            findings = validate_pack(Path(tmp), self.index)
            self.assertEqual([], _errors(findings))

    def test_packid_inconsistency_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._pack(tmp, ["pack-metadata"])
            other = json.loads(FAMILY_EXAMPLE["lifecycle"].read_text(encoding="utf-8"))
            other["packId"] = "a-different-pack"
            (Path(tmp) / "lifecycle.json").write_text(json.dumps(other), encoding="utf-8")
            findings = validate_pack(Path(tmp), self.index)
            self.assertTrue(any(f.check == "packid" for f in _errors(findings)))

    def test_artifact_boundary_traversal_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "artifact-boundary.json").write_text(
                json.dumps(
                    {"packId": "p", "artifacts": [{"path": "../escape.md", "disposition": "authored"}]}
                ),
                encoding="utf-8",
            )
            findings = validate_pack(Path(tmp), self.index)
            self.assertTrue(any(f.check == "artifact-boundary" for f in _errors(findings)))

    def test_empty_directory_flags_missing_required_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings = validate_pack(Path(tmp), self.index)
            errors = _errors(findings)
            self.assertTrue(errors)
            missing = {f.family for f in errors if f.check == "pack"}
            for family in ("pack-metadata", "compatibility", "provenance", "lifecycle"):
                self.assertIn(family, missing)

    def test_partial_pack_flags_only_the_missing_required_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._pack(tmp, ["pack-metadata", "compatibility", "provenance"])
            errors = _errors(validate_pack(Path(tmp), self.index))
            missing = {f.family for f in errors if f.check == "pack"}
            self.assertEqual({"lifecycle"}, missing)

    def test_symlinked_record_escaping_root_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside.json"
            outside.write_text(json.dumps({"packId": "p"}), encoding="utf-8")
            pack = Path(tmp) / "pack"
            pack.mkdir()
            self._pack(pack, ["pack-metadata", "compatibility", "provenance", "lifecycle"])
            link = pack / "artifact-boundary.json"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unsupported on this platform")
            findings = validate_pack(pack, self.index)
            self.assertTrue(any("symlink" in f.message for f in _errors(findings)))
            self.assertTrue(all(not Path(f.path).is_absolute() for f in findings))


class CliContractTests(unittest.TestCase):
    def _run(self, *args):
        env = {"PYTHONPATH": str(TOOLS), "PATH": __import__("os").environ.get("PATH", "")}
        return subprocess.run(
            [sys.executable, "-m", "aces_pack_tools", *args],
            capture_output=True, text=True, cwd=str(ROOT), env=env,
        )

    def test_help_exits_zero(self):
        self.assertEqual(0, self._run("--help").returncode)

    def test_validate_clean_record_exits_zero(self):
        result = self._run("validate", str(FAMILY_EXAMPLE["release"]),
                           "--family", "release", "--schema-index", str(INDEX))
        self.assertEqual(0, result.returncode, result.stderr)

    def test_validate_bad_record_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "validation.json"
            bad.write_text(json.dumps({"checks": []}), encoding="utf-8")
            result = self._run("validate", str(bad), "--family", "validation",
                               "--schema-index", str(INDEX))
            self.assertEqual(1, result.returncode)

    def test_missing_schema_index_is_usage_error(self):
        result = self._run("validate", str(FAMILY_EXAMPLE["release"]),
                           "--family", "release", "--schema-index", "/no/such/index.json")
        self.assertEqual(2, result.returncode)

    def test_json_output_is_parseable(self):
        result = self._run("validate", str(FAMILY_EXAMPLE["release"]),
                           "--family", "release", "--schema-index", str(INDEX), "--format", "json")
        payload = json.loads(result.stdout)
        self.assertIn("findings", payload)
        self.assertEqual([], payload["findings"])

    def _visibility_pack(self, tmp, roots, files=()):
        for rel, content in files:
            target = Path(tmp) / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        (Path(tmp) / "runtime-visibility.json").write_text(
            json.dumps({"packId": "p", "roots": roots}), encoding="utf-8"
        )

    def test_visibility_clean_pack_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._visibility_pack(
                tmp,
                [{"path": "public/", "visibility": "participant-visible"}],
                files=[("public/readme.md", "A portable ACES scenario brief.")],
            )
            result = self._run("visibility", tmp, "--schema-index", str(INDEX))
            self.assertEqual(0, result.returncode, result.stderr)

    def test_visibility_leaking_pack_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._visibility_pack(
                tmp,
                [{"path": "public/", "visibility": "participant-visible"}],
                files=[("public/leak.md", "key = AKIA" + "ABCDEFGHIJKLMNOP")],
            )
            result = self._run("visibility", tmp, "--schema-index", str(INDEX))
            self.assertEqual(1, result.returncode)

    def test_visibility_pack_without_record_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run("visibility", tmp, "--schema-index", str(INDEX))
            self.assertEqual(0, result.returncode, result.stderr)


class CiExampleTests(unittest.TestCase):
    WORKFLOW = ROOT / "examples" / "ci" / "validate-pack.yml"

    def test_example_workflow_exists(self):
        self.assertTrue(self.WORKFLOW.exists(), f"missing CI example: {self.WORKFLOW}")

    def test_example_invokes_the_real_cli(self):
        text = self.WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("aces_pack_tools", text)
        self.assertTrue(any(cmd in text for cmd in ("validate", "leak", "release", "check")))

    def test_example_requires_no_secrets(self):
        text = self.WORKFLOW.read_text(encoding="utf-8").lower()
        for forbidden in ("secrets.", "sonar_token", "${{ secrets"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
