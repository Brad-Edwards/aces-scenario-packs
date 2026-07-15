"""Gate-infrastructure tests for the repo-wide scenario-content CI helper.

These exercise the helper itself (not scenario packs), so the CI workflow runs
them alongside the pack gate. The load-bearing invariant under test: a
visibility-leak failure must report the operator-token *class* and a
token-independent locator (file path + line number), and must NOT emit the raw
token body OR any token-derived verifier (e.g. a hash of the match) — otherwise
the gate that exists to keep operator tokens off participant-facing surfaces
would itself leak them into the (quasi-public) Actions log. The operator-token
vocabularies are low-entropy (operator states, ATT&CK technique ids), so even a
truncated digest is reversible by precomputation and is not acceptable
(issue #138).
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import tempfile
import unittest
from unittest import mock

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.join(os.path.dirname(_HERE), "src", "aces_scenario_packs")
_CI_PATH = os.path.join(_PKG, "content_ci.py")
_SCAFFOLD_PATH = os.path.join(_PKG, "new_pack.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("scenario_content_ci_undertest", _CI_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


CI = _load_module()


def _load_scaffold_module():
    spec = importlib.util.spec_from_file_location(
        "new_scenario_pack_undertest", _SCAFFOLD_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


SCAFFOLD = _load_scaffold_module()

# Representative operator tokens that must never reach a participant surface.
TOKEN_EXAMPLES = [
    ("restricted S-* state", "S-EXFILSTAGE"),
    ("source label", "S1.12"),    # source label S1.*/S2.*
    ("ATT&CK", "T1059.003"),      # ATT&CK technique id
    ("attack-path", "7.B"),       # attack-path step id
]
OPERATOR_STATE_TOKEN = TOKEN_EXAMPLES[0][1]
TECH_TOKEN = TOKEN_EXAMPLES[2][1]


def _digest(tok: str) -> str:
    """The reversible verifier the gate must NOT emit (regression guard)."""
    return hashlib.sha256(tok.encode("utf-8")).hexdigest()[:12]


class TokenLeakRedactionTest(unittest.TestCase):
    def _write(self, body: str) -> str:
        fh = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        fh.write(body)
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def test_token_leaks_reports_line_not_token_or_verifier(self):
        for expected_label, token in TOKEN_EXAMPLES:
            with self.subTest(token_class=expected_label):
                path = self._write(f"first line\nbriefing mentioning {token} inline\n")
                leaks = CI._token_leaks(path)
                self.assertEqual(len(leaks), 1)
                label, locator = leaks[0]
                self.assertIn(expected_label, label)
                # Locator is the token-independent line number (here: line 2);
                # the label must stay class-only, never the token body or a hash
                # of it.
                self.assertEqual(locator, 2)
                self.assertNotIn(token, label)
                self.assertNotIn(_digest(token), label)

    def test_clean_file_has_no_leaks(self):
        path = self._write("ordinary participant briefing, nothing hidden here\n")
        self.assertEqual(CI._token_leaks(path), [])


class VisibilityScanRedactionTest(unittest.TestCase):
    def test_failure_message_emits_no_token_derived_content(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        content = os.path.join(scen, "fakepack", "assets", "content")
        os.makedirs(content)
        with open(os.path.join(scen, "fakepack", "pack.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("name: fakepack\n")
        with open(os.path.join(content, "leak.md"), "w", encoding="utf-8") as fh:
            fh.write(f"oops the answer is {TECH_TOKEN}\n")

        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_visibility(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        blob = "\n".join(failures)
        self.assertTrue(any("VISIBILITY LEAK" in f for f in failures), blob)
        # Neither the raw token nor a precomputable verifier of it may appear.
        self.assertNotIn(TECH_TOKEN, blob)
        self.assertNotIn(_digest(TECH_TOKEN), blob)
        # The locator (path, and the line the match is on) must still be present.
        self.assertIn("leak.md", blob)

    def test_challenge_text_is_participant_visible(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        challenges = os.path.join(scen, "fakepack", "challenges")
        os.makedirs(challenges)
        with open(os.path.join(scen, "fakepack", "pack.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("name: fakepack\n")
        with open(os.path.join(challenges, "challenge.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(f"challenge copy leaked {TECH_TOKEN}\n")

        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_visibility(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        blob = "\n".join(failures)
        self.assertIn("VISIBILITY LEAK", blob)
        self.assertIn("challenges/challenge.md", blob)
        self.assertNotIn(TECH_TOKEN, blob)
        self.assertIn(":1", blob)


class AntiExtensionGuardTest(unittest.TestCase):
    """The zero-extensions guard (issue #83 / ADR 0009).

    The guard is structural: a removed ACES-semantic concept is forbidden as a
    *declared* schema property or manifest key and as an ``sdl/`` semantic ledger,
    never as a word in prose. These tests lock that the shipped format is clean
    and that a reintroduced layer or ledger is caught wherever it can slip in.
    """

    def test_shipped_format_has_no_extension_layers(self):
        # The real bundled schema, template, and example must pass the guard.
        failures: list[str] = []
        CI.check_anti_extension(failures)
        self.assertEqual(failures, [], "\n".join(failures))

    def test_forbidden_manifest_keys_detects_removed_layers(self):
        manifest = {"schema_version": 1, "pack": {}, "scoring": {}, "telemetry": {}}
        self.assertEqual(
            CI._forbidden_manifest_keys(manifest), ["scoring", "telemetry"])

    def test_forbidden_manifest_keys_clean_manifest(self):
        self.assertEqual(
            CI._forbidden_manifest_keys({"pack": {}, "assets": [], "validation": {}}), [])

    def test_schema_reintroducing_layer_is_flagged(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        with open(os.path.join(tmp, CI.COMPATIBILITY_SCHEMA_FILE), "w",
                  encoding="utf-8") as fh:
            fh.write("type: object\nproperties:\n  telemetry:\n    type: object\n")
        orig = CI._SCHEMAS_DIR
        CI._SCHEMAS_DIR = tmp
        try:
            failures: list[str] = []
            CI._check_schema_no_extension_layers(failures)
        finally:
            CI._SCHEMAS_DIR = orig
        blob = "\n".join(failures)
        self.assertIn("ANTI-EXTENSION", blob)
        self.assertIn("telemetry", blob)

    def test_pack_manifest_reintroducing_layer_is_flagged(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        pack = os.path.join(scen, "example-pack")
        os.makedirs(pack)
        with open(os.path.join(pack, "pack.yaml"), "w", encoding="utf-8") as fh:
            fh.write("name: example-pack\ncompatibility_manifest: pack.compatibility.yaml\n")
        with open(os.path.join(pack, "pack.compatibility.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("schema_version: 1\nscoring:\n  status: not_shipped\n")
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI._check_pack_no_extension_layers("example-pack", failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo
        blob = "\n".join(failures)
        self.assertIn("ANTI-EXTENSION", blob)
        self.assertIn("scoring", blob)

    def test_pack_sdl_semantic_ledger_is_flagged(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        sdl = os.path.join(scen, "example-pack", "sdl")
        os.makedirs(sdl)
        open(os.path.join(sdl, "scoring.yaml"), "w").close()
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI._check_pack_no_extension_layers("example-pack", failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo
        self.assertIn("sdl/scoring.yaml", "\n".join(failures))

    def test_clean_pack_passes(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        sdl = os.path.join(scen, "example-pack", "sdl")
        os.makedirs(sdl)
        # A legitimate ACES SDL document is not a forbidden ledger.
        open(os.path.join(sdl, "example.sdl.yaml"), "w").close()
        with open(os.path.join(scen, "example-pack", "pack.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("name: example-pack\n")
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI._check_pack_no_extension_layers("example-pack", failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo
        self.assertEqual(failures, [])


class AntiExtensionAggregatorTest(unittest.TestCase):
    """Drive the public ``check_anti_extension`` aggregator — the one ``main()``
    actually calls — not just its leaf helpers.

    ``AntiExtensionGuardTest`` exercises the leaf checks directly, so the
    aggregator's own wiring (the per-pack loop and the packaged template/example
    branch) would be untested through the public entry point: against the real
    repo there is no ``scenarios/`` tree, so the loop body never runs and the
    packaged-manifest failure branch never fires. A refactor that dropped either
    call from ``check_anti_extension`` would keep the suite green while the guard
    silently stopped enforcing the charter in production (issue #83 / ADR 0009).
    This class closes that gap, mirroring ``ProvenanceWrapperGateTest``.
    """

    def test_aggregator_flags_pack_reintroducing_layer(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        pack = os.path.join(scen, "example-pack")
        os.makedirs(pack)
        with open(os.path.join(pack, "pack.yaml"), "w", encoding="utf-8") as fh:
            fh.write("name: example-pack\ncompatibility_manifest: pack.compatibility.yaml\n")
        with open(os.path.join(pack, "pack.compatibility.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("schema_version: 1\nscoring:\n  status: not_shipped\n")
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_anti_extension(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo
        self.assertTrue(
            any("ANTI-EXTENSION" in f and "scoring" in f for f in failures),
            "\n".join(failures))

    def test_aggregator_flags_packaged_template_manifest(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        # A corrupted copy of the packaged template manifest, reached only through
        # the aggregator's packaged-manifest branch (not the leaf helper).
        with open(os.path.join(tmp, CI.COMPATIBILITY_MANIFEST_FILE), "w",
                  encoding="utf-8") as fh:
            fh.write("schema_version: 1\ntelemetry:\n  status: not_shipped\n")
        empty_scen = os.path.join(tmp, "scenarios")
        os.makedirs(empty_scen)
        orig_tmpl, orig_scen, orig_repo = CI._TEMPLATE_DIR, CI.SCEN, CI._REPO
        CI._TEMPLATE_DIR, CI.SCEN, CI._REPO = tmp, empty_scen, tmp
        try:
            failures: list[str] = []
            CI.check_anti_extension(failures)
        finally:
            CI._TEMPLATE_DIR, CI.SCEN, CI._REPO = orig_tmpl, orig_scen, orig_repo
        blob = "\n".join(failures)
        self.assertTrue(any("ANTI-EXTENSION" in f for f in failures), blob)
        self.assertIn("telemetry", blob)


class PackDiscoveryTest(unittest.TestCase):
    def _with_temp_catalog(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        os.makedirs(scen, exist_ok=True)
        return tmp, scen

    def test_only_direct_manifest_bearing_directories_are_packs(self):
        _tmp, scen = self._with_temp_catalog()
        os.makedirs(os.path.join(scen, "design-notes"))
        os.makedirs(os.path.join(scen, "legacy-scenario", "sdl"))
        os.makedirs(os.path.join(scen, "real-pack"))
        os.makedirs(os.path.join(scen, "alpha-pack"))
        with open(os.path.join(scen, "real-pack", "pack.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("name: real-pack\n")
        with open(os.path.join(scen, "alpha-pack", "pack.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("name: alpha-pack\n")

        self.assertEqual(CI._packs(scen), ("alpha-pack", "real-pack"))

    def test_marker_bearing_template_is_a_pack_candidate(self):
        _tmp, scen = self._with_temp_catalog()
        template = os.path.join(scen, "_template")
        os.makedirs(template)
        with open(os.path.join(template, "pack.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("not: valid: yaml\n")

        self.assertEqual(CI._packs(scen), ("_template",))

    def test_symlinked_marker_remains_a_candidate_for_static_rejection(self):
        tmp, scen = self._with_temp_catalog()
        pack = os.path.join(scen, "linked-marker")
        os.makedirs(pack)
        target = os.path.join(tmp, "outside.yaml")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("name: linked-marker\n")
        os.symlink(target, os.path.join(pack, "pack.yaml"))

        self.assertEqual(CI._packs(scen), ("linked-marker",))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation is not supported")
    def test_special_file_marker_remains_a_candidate_for_static_rejection(self):
        _tmp, scen = self._with_temp_catalog()
        pack = os.path.join(scen, "special-marker")
        os.makedirs(pack)
        os.mkfifo(os.path.join(pack, "pack.yaml"))

        self.assertEqual(CI._packs(scen), ("special-marker",))

    def test_symlinked_pack_directory_is_not_followed(self):
        tmp, scen = self._with_temp_catalog()
        outside = os.path.join(tmp, "outside-pack")
        os.makedirs(outside)
        with open(os.path.join(outside, "pack.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("name: outside-pack\n")
        os.symlink(outside, os.path.join(scen, "linked-pack"))

        self.assertEqual(CI._packs(scen), ())

    def test_absent_scenarios_directory_is_an_empty_catalog(self):
        tmp, _scen = self._with_temp_catalog()
        missing = os.path.join(tmp, "missing")

        self.assertEqual(CI._packs(missing), ())

    def test_unreadable_catalog_fails_closed_without_raw_exception(self):
        _tmp, scen = self._with_temp_catalog()
        failures: list[str] = []
        with mock.patch.object(CI.os, "scandir", side_effect=OSError("secret path")):
            self.assertEqual(CI._packs(scen, failures), ())

        self.assertEqual(len(failures), 1)
        self.assertIn("CATALOG DISCOVERY FAILED", failures[0])
        self.assertNotIn("secret path", failures[0])

    def test_unreadable_candidate_redacts_its_name_and_raw_exception(self):
        _tmp, scen = self._with_temp_catalog()
        secret_name = "credential-token"
        blocked = os.path.join(scen, secret_name)
        os.makedirs(blocked)
        real_scandir = os.scandir

        def fail_one(path):
            if os.path.abspath(path) == os.path.abspath(blocked):
                raise OSError("raw secret exception")
            return real_scandir(path)

        failures: list[str] = []
        with mock.patch.object(CI.os, "scandir", side_effect=fail_one):
            self.assertEqual(CI._packs(scen, failures), ())

        self.assertEqual(
            failures,
            ["CATALOG DISCOVERY FAILED: scenarios/<entry>/ could not be inspected"],
        )
        self.assertNotIn(secret_name, failures[0])
        self.assertNotIn("raw secret exception", failures[0])


class AuthorCiDiscoveryFlowTest(unittest.TestCase):
    def test_main_discovers_once_and_executes_code_only_for_static_valid_packs(self):
        valid = CI._AuthorStaticView((), (), (), (), ())
        invalid = CI._AuthorStaticView(("invalid",), (), (), (), ())
        events: list[tuple[str, tuple[str, ...]]] = []

        def static_check(_failures, packs):
            events.append(("static", packs))
            return {"valid": valid, "invalid": invalid}

        def record(name):
            return lambda _failures, packs, *args: events.append((name, packs))

        def record_with_views(name):
            return lambda _failures, _views, packs: events.append((name, packs))

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(CI, "_packs", return_value=("valid", "invalid")) as discover, \
                mock.patch.object(CI, "check_static_contract", side_effect=static_check), \
                mock.patch.object(CI, "check_validators", side_effect=record("validators")), \
                mock.patch.object(CI, "check_tests", side_effect=record("tests")), \
                mock.patch.object(CI, "check_sdl", side_effect=record_with_views("sdl")), \
                mock.patch.object(CI, "check_visibility", side_effect=record("visibility")), \
                mock.patch.object(CI, "check_manifest", side_effect=record_with_views("manifest")), \
                mock.patch.object(CI, "check_anti_extension", side_effect=record("anti-extension")), \
                mock.patch.object(CI, "check_provenance", side_effect=record_with_views("provenance")), \
                mock.patch.object(CI, "check_golden_checklist", side_effect=record("golden")):
            self.assertEqual(CI.main(["--repo", tmp]), 0)

        discover.assert_called_once()
        self.assertEqual(events[0], ("static", ("valid", "invalid")))
        self.assertEqual(events[1:3], [
            ("validators", ("valid",)),
            ("tests", ("valid",)),
        ])
        self.assertTrue(all(packs == ("valid", "invalid")
                            for _name, packs in events[3:]))


class NewScenarioPackScaffoldTest(unittest.TestCase):
    def test_repo_root_accepts_gitfile_worktree_checkout(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        os.makedirs(os.path.join(tmp, "scenarios"), exist_ok=True)
        with open(os.path.join(tmp, ".git"), "w", encoding="utf-8") as fh:
            fh.write("gitdir: /tmp/example.git/worktrees/example\n")

        self.assertEqual(SCAFFOLD.repo_root(tmp), tmp)


class GoldenChecklistGateTest(unittest.TestCase):
    def _with_pack(self, checklist_body: str | None):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        docs = os.path.join(scen, "fakepack", "docs")
        os.makedirs(docs, exist_ok=True)
        with open(os.path.join(scen, "fakepack", "pack.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("name: fakepack\n")
        if checklist_body is not None:
            with open(os.path.join(docs, "golden-readiness-checklist.md"),
                      "w", encoding="utf-8") as fh:
                fh.write(checklist_body)
        return tmp, scen

    def test_missing_checklist_is_flagged(self):
        tmp, scen = self._with_pack(None)
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_golden_checklist(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        self.assertTrue(any("golden checklist MISSING" in f for f in failures))

    def test_checklist_must_have_manual_protocol_and_tick_boxes(self):
        tmp, scen = self._with_pack("# Golden\n\nNo checklist here.\n")
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_golden_checklist(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        blob = "\n".join(failures)
        self.assertIn("golden checklist INCOMPLETE", blob)
        self.assertIn("Final Manual Participant Walkthrough Protocol", blob)
        self.assertIn("- [ ]", blob)

    def test_complete_checklist_is_clean(self):
        body = "\n".join([
            "# Golden Readiness Checklist",
            "## Golden Definition Of Done",
            "- [ ] applies cleanly",
            "## Final Manual Participant Walkthrough Protocol",
            "- [ ] enter through participant surface",
        ])
        tmp, scen = self._with_pack(body)
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_golden_checklist(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        self.assertEqual(failures, [])


class CompatibilityManifestGateTest(unittest.TestCase):
    def _with_manifest_pack(self, manifest_body: str, pack_body: str | None = None):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        pack = os.path.join(scen, "example-pack")
        os.makedirs(pack, exist_ok=True)
        os.makedirs(os.path.join(scen, "_template"), exist_ok=True)
        shutil.copyfile(CI.compatibility_schema_path(), os.path.join(
            scen, "pack-compatibility.schema.yaml"))
        shutil.copyfile(CI.compatibility_example_path(), os.path.join(
            scen, "_template", "pack.compatibility.example.yaml"))
        with open(os.path.join(pack, "pack.yaml"), "w", encoding="utf-8") as fh:
            fh.write(pack_body or "\n".join([
                "name: example-pack",
                'title: "Example Pack"',
                "version: 0.1.0",
                "status: draft",
                'description: "An example scenario pack."',
                "authors:",
                "  - ACES <noreply@example.com>",
                'license: "© 2026 Example Org. All rights reserved."',
                "requirement: null",
                "contents:",
                "  flag_layer: false",
                "  reference_triangle: false",
                "  profile_bundles: false",
                "compatibility_manifest: pack.compatibility.yaml",
            ]))
        with open(os.path.join(pack, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("# Example Pack\n")
        with open(os.path.join(pack, "pack.compatibility.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write(manifest_body)
        return tmp, scen

    def _valid_manifest(self) -> str:
        return "\n".join([
            "schema_version: scenario-pack-compatibility/v1",
            "pack:",
            "  name: example-pack",
            '  title: "Example Pack"',
            "  version: 0.1.0",
            "  status: draft",
            "  source:",
            "    requirement: null",
            "    issues: [44]",
            "    upstream_references: []",
            "artifact_boundaries:",
            "  participant_visible:",
            "    - path: README.md",
            "      export: public",
            "  operator_only: []",
            "  oracle_only: []",
            "  commercial: []",
            "runtime_profiles: []",
            "delivery_bundles: []",
            "platform_features: []",
            "assets: []",
            "operator_surfaces: []",
            "validation:",
            "  commands:",
            "    - id: manifest",
            "      command: python3 scripts/ci/scenario_content_ci.py",
            "      validates: [manifest]",
            "  gates: []",
        ])

    def test_valid_compatibility_manifest_is_clean(self):
        tmp, scen = self._with_manifest_pack(self._valid_manifest())
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_manifest(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        self.assertEqual(failures, [])

    def test_compatibility_manifest_rejects_pack_name_mismatch(self):
        body = self._valid_manifest().replace("name: example-pack", "name: other-pack")
        tmp, scen = self._with_manifest_pack(body)
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_manifest(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        self.assertIn("pack name mismatch", "\n".join(failures))

    def test_compatibility_manifest_rejects_duplicate_ids(self):
        body = self._valid_manifest().replace(
            "platform_features: []",
            "\n".join([
                "platform_features:",
                "  - feature_id: aws",
                "    status: required",
                "    description: AWS range support.",
                "  - feature_id: aws",
                "    status: required",
                "    description: duplicate",
            ]),
        )
        tmp, scen = self._with_manifest_pack(body)
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_manifest(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        self.assertIn("duplicate feature_id", "\n".join(failures))

    def test_compatibility_manifest_rejects_path_escape(self):
        body = self._valid_manifest().replace("path: README.md", "path: ../secret.txt")
        tmp, scen = self._with_manifest_pack(body)
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_manifest(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        self.assertIn("path escapes pack root", "\n".join(failures))

    def test_compatibility_manifest_rejects_export_parent_of_oracle_path(self):
        body = self._valid_manifest().replace(
            "  operator_only: []",
            "\n".join([
                "  operator_only:",
                "    - path: docs/",
                "      export: commercial",
            ]),
        ).replace(
            "  oracle_only: []",
            "\n".join([
                "  oracle_only:",
                "    - path: docs/oracle-map.md",
                "      export: private",
            ]),
        )
        tmp, scen = self._with_manifest_pack(body)
        docs = os.path.join(scen, "example-pack", "docs")
        os.makedirs(docs, exist_ok=True)
        with open(os.path.join(docs, "oracle-map.md"), "w", encoding="utf-8") as fh:
            fh.write("hidden proof\n")
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_manifest(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

        self.assertIn("contains oracle/private path", "\n".join(failures))

    def test_template_example_validates_against_schema(self):
        failures: list[str] = []
        CI.check_compatibility_schema_example(failures)
        self.assertEqual(failures, [])

    def test_template_example_covers_standard_delivery_bundles(self):
        failures: list[str] = []
        example = CI._load_yaml(
            CI.compatibility_example_path(), failures, "compatibility example")
        self.assertEqual(failures, [])

        bundles = example.get("delivery_bundles", [])
        by_audience = {
            row.get("audience"): row
            for row in bundles
            if isinstance(row, dict)
        }
        expected = {"guided", "unguided", "purple-team", "agent-benchmark", "demo"}
        self.assertEqual(set(by_audience), expected)
        for audience, row in by_audience.items():
            with self.subTest(audience=audience):
                self.assertEqual(row.get("status"), "supported")
                self.assertEqual(row.get("manifest", {}).get("path"),
                                 "profiles/bundles.yaml")
                self.assertEqual(
                    row.get("validation", [{}])[0].get("path"),
                    "profiles/validate_profiles.py")


class NewScenarioPackScriptTest(unittest.TestCase):
    def _temp_repo(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        os.makedirs(os.path.join(tmp, ".git"))
        template = os.path.join(tmp, "scenarios", "_template")
        os.makedirs(os.path.join(template, "docs"), exist_ok=True)
        with open(os.path.join(template, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("# `<name>` -- scenario pack\n")
        with open(os.path.join(template, "pack.yaml"), "w", encoding="utf-8") as fh:
            fh.write("\n".join([
                "name: <name>",
                'title: "Human-readable title"',
                'description: "One line: what the scenario is and what the player does."',
                "requirement: null",
            ]))
        with open(os.path.join(template, "pack.compatibility.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("\n".join([
                "pack:",
                "  name: <name>",
                '  title: "Human-readable title"',
                "  source:",
                "    requirement: null",
            ]))
        with open(os.path.join(template, "docs", "golden-readiness-checklist.md"),
                  "w", encoding="utf-8") as fh:
            fh.write("# Golden Readiness Checklist\n")
        return tmp

    def test_scaffold_rejects_non_kebab_pack_id(self):
        with self.assertRaises(SystemExit):
            SCAFFOLD.validate_pack_id("../bad")

    def test_scaffold_copies_template_and_patches_identity(self):
        repo = self._temp_repo()
        target = SCAFFOLD.scaffold_pack(
            repo,
            "test-scenario",
            "Test Scenario",
            "A test scenario.",
            "TST-0001",
            123,
        )

        self.assertTrue(os.path.isdir(target))
        with open(os.path.join(target, "pack.yaml"), encoding="utf-8") as fh:
            pack = fh.read()
        with open(os.path.join(target, "pack.compatibility.yaml"), encoding="utf-8") as fh:
            compatibility = fh.read()
        with open(os.path.join(target, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertIn("name: test-scenario", pack)
        self.assertIn('title: "Test Scenario"', pack)
        self.assertIn("requirement: TST-0001", pack)
        self.assertIn("name: test-scenario", compatibility)
        self.assertIn("requirement: TST-0001", compatibility)
        self.assertIn("Created from GitHub issue #123", readme)
        self.assertTrue(os.path.isfile(os.path.join(
            target, "docs", "golden-readiness-checklist.md")))


def _valid_ledger(name: str = "testpack") -> dict:
    """A minimal ledger that satisfies the provenance schema + gate."""
    return {
        "schema_version": "scenario-pack-provenance/v2",
        "pack": {"name": name},
        "sources": [
            {"source_id": "original-design",
             "name": "Original design", "license": "proprietary",
             "usage": "reused", "attribution_required": False},
        ],
        "artifacts": [
            {"artifact_id": "docs", "path": "docs/",
             "classification": "commercial-only", "sources": ["original-design"]},
        ],
        "content_safety": {
            "no_real_malware": True, "no_real_third_party_targets": True,
            "no_real_credentials": True, "no_sensitive_data": True,
            "offensive_tooling_boundary": True},
        "review": {"status": "pending", "gates": [
            {"gate_id": "licensing", "status": "pending"},
            {"gate_id": "attribution", "status": "pending"},
            {"gate_id": "sensitive-data", "status": "pending"},
            {"gate_id": "offensive-tooling", "status": "pending"}]},
    }


class ProvenanceLedgerGateTest(unittest.TestCase):
    """Gate-infra tests for the provenance ledger validator (issue #48)."""

    PACK = "testpack"

    def _build(self, ledger, *, write_pointer=True,
               pointer="docs/provenance-ledger.yaml", extra_dirs=()):
        # Copy the real schema before SCEN is repointed at the temp tree.
        real_schema = CI.provenance_schema_path()
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        os.makedirs(scen)
        shutil.copy(real_schema, os.path.join(scen, CI.PROVENANCE_SCHEMA_FILE))
        pack_root = os.path.join(scen, self.PACK)
        os.makedirs(os.path.join(pack_root, "docs"))
        for d in extra_dirs:
            os.makedirs(os.path.join(pack_root, d), exist_ok=True)
        if ledger is not None:
            with open(os.path.join(pack_root, "docs", "provenance-ledger.yaml"),
                      "w", encoding="utf-8") as fh:
                yaml.safe_dump(ledger, fh)
        pack_yaml = {"name": self.PACK}
        if write_pointer:
            pack_yaml["provenance_ledger"] = pointer
        with open(os.path.join(pack_root, "pack.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(pack_yaml, fh)
        return tmp, scen, pack_yaml

    def _run(self, ledger, **kw):
        tmp, scen, pack_yaml = self._build(ledger, **kw)
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI._validate_provenance_ledger(self.PACK, pack_yaml, failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo
        return failures

    def test_valid_ledger_passes(self):
        self.assertEqual(self._run(_valid_ledger()), [])

    def test_missing_pointer_is_flagged(self):
        blob = "\n".join(self._run(_valid_ledger(), write_pointer=False))
        self.assertIn("no provenance_ledger pointer", blob)

    def test_pointer_path_escape_is_flagged(self):
        blob = "\n".join(self._run(_valid_ledger(),
                                   pointer="../escape.yaml"))
        self.assertIn("escapes pack root", blob)

    def test_missing_ledger_file_is_flagged(self):
        blob = "\n".join(self._run(None))
        self.assertIn("provenance ledger MISSING", blob)

    def test_schema_violation_is_flagged(self):
        bad = _valid_ledger()
        bad["sources"][0]["usage"] = "not-a-usage"
        blob = "\n".join(self._run(bad))
        self.assertIn("INVALID", blob)

    def test_reintroduced_source_kind_is_rejected(self):
        # `sources[].kind` was removed (ADR 0014); the closed schema rejects it
        # as an unknown field so a governed concept vocabulary cannot return.
        bad = _valid_ledger()
        bad["sources"][0]["kind"] = "framework"
        blob = "\n".join(self._run(bad))
        self.assertIn("INVALID", blob)

    def test_empty_artifacts_is_flagged(self):
        # A pack with no classified artifact roots has not declared its
        # distribution boundary — the gate must reject it.
        bad = _valid_ledger()
        bad["artifacts"] = []
        blob = "\n".join(self._run(bad))
        self.assertIn("INVALID", blob)

    def test_pack_name_mismatch_is_flagged(self):
        bad = _valid_ledger("wrong-name")
        blob = "\n".join(self._run(bad))
        self.assertIn("pack name mismatch", blob)

    def test_unsafe_content_attestation_is_flagged(self):
        bad = _valid_ledger()
        bad["content_safety"]["no_real_malware"] = False
        blob = "\n".join(self._run(bad))
        self.assertIn("content_safety.no_real_malware must be true", blob)

    def test_missing_required_review_gate_is_flagged(self):
        bad = _valid_ledger()
        bad["review"]["gates"] = [g for g in bad["review"]["gates"]
                                  if g["gate_id"] != "offensive-tooling"]
        blob = "\n".join(self._run(bad))
        self.assertIn("missing required gate offensive-tooling", blob)

    def test_attribution_required_without_text_is_flagged(self):
        bad = _valid_ledger()
        bad["sources"][0]["attribution_required"] = True
        blob = "\n".join(self._run(bad))
        self.assertIn("attribution_required", blob)

    def test_unknown_source_ref_is_flagged(self):
        bad = _valid_ledger()
        bad["artifacts"][0]["sources"] = ["ghost-source"]
        blob = "\n".join(self._run(bad))
        self.assertIn("unknown source_id ghost-source", blob)

    def test_missing_artifact_path_is_flagged(self):
        bad = _valid_ledger()
        bad["artifacts"][0]["path"] = "nope/"
        blob = "\n".join(self._run(bad))
        self.assertIn("references missing path", blob)

    def test_customer_specific_outside_overlay_is_flagged(self):
        bad = _valid_ledger()
        bad["artifacts"].append({
            "artifact_id": "leak", "path": "secret/",
            "classification": "customer-specific", "sources": ["original-design"]})
        blob = "\n".join(self._run(bad, extra_dirs=("secret",)))
        self.assertIn("not under a declared overlay root", blob)

    def test_overlay_overlapping_base_root_is_flagged(self):
        bad = _valid_ledger()
        bad["overlays"] = [{"overlay_id": "acme", "root": "docs/",
                            "classification": "customer-specific"}]
        blob = "\n".join(self._run(bad))
        self.assertIn("overlaps base artifact path", blob)

    def test_customer_specific_under_declared_overlay_passes(self):
        ok = _valid_ledger()
        ok["overlays"] = [{"overlay_id": "acme", "root": "overlays/acme/",
                           "classification": "customer-specific"}]
        ok["artifacts"].append({
            "artifact_id": "branding", "path": "overlays/acme/branding.md",
            "classification": "customer-specific", "sources": ["original-design"]})
        tmp, scen, pack_yaml = self._build(ok, extra_dirs=("overlays/acme",))
        # The overlay artifact file must exist for the path-existence check.
        open(os.path.join(scen, self.PACK, "overlays", "acme", "branding.md"),
             "w").close()
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI._validate_provenance_ledger(self.PACK, pack_yaml, failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo
        self.assertEqual(failures, [])


class ProvenanceWrapperGateTest(unittest.TestCase):
    """Drive the top-level check_provenance wrapper (not the inner validator).

    The ProvenanceLedgerGateTest cases call _validate_provenance_ledger directly,
    so the wrapper's own logic — the schema-example check and the pack-iteration
    loop — would be untested without this class. A no-op wrapper, a swallowed
    schema-example failure, or a silently-skipped pack must not stay green.
    """

    def _build_tree(self, *, write_pointer=True):
        real_schema = CI.provenance_schema_path()
        real_example = CI.provenance_example_path()
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        os.makedirs(scen)
        shutil.copy(real_schema, os.path.join(scen, CI.PROVENANCE_SCHEMA_FILE))
        # check_provenance_schema_example reads the _template example.
        tmpl_docs = os.path.join(scen, "_template", "docs")
        os.makedirs(tmpl_docs)
        shutil.copy(real_example,
                    os.path.join(tmpl_docs, "provenance-ledger.example.yaml"))
        # One real pack with a valid ledger.
        pack_root = os.path.join(scen, "realpack")
        os.makedirs(os.path.join(pack_root, "docs"))
        pack_yaml = {"name": "realpack"}
        if write_pointer:
            pack_yaml["provenance_ledger"] = "docs/provenance-ledger.yaml"
        with open(os.path.join(pack_root, "pack.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(pack_yaml, fh)
        with open(os.path.join(pack_root, "docs", "provenance-ledger.yaml"),
                  "w", encoding="utf-8") as fh:
            yaml.safe_dump(_valid_ledger("realpack"), fh)
        return tmp, scen

    def _run(self, **kw):
        tmp, scen = self._build_tree(**kw)
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            CI.check_provenance(failures)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo
        return failures

    def test_wrapper_passes_on_valid_tree(self):
        self.assertEqual(self._run(), [])

    def test_wrapper_flags_pack_missing_pointer(self):
        # A no-op wrapper or a silently-skipped pack would lose this failure.
        blob = "\n".join(self._run(write_pointer=False))
        self.assertIn("no provenance_ledger pointer", blob)


class ProvenanceRealRepoGateTest(unittest.TestCase):
    """The real schema, example, and every shipped pack ledger validate clean."""

    def test_provenance_gate_is_clean(self):
        failures: list[str] = []
        CI.check_provenance(failures)
        self.assertEqual(failures, [], "\n".join(failures))


_VALID_SDL = "\n".join([
    "name: example-pack",
    "nodes:",
    "  boreas-mail:",
    "    type: vm",
    "",
])
# `nodes.<id>` with no `type` is rejected by ACES semantic validation — a
# genuinely invalid SDL document, validated *through ACES* (no local schema).
_INVALID_SDL = "\n".join([
    "name: example-pack",
    "nodes:",
    "  boreas-mail: {}",
    "",
])


class SdlValidationGateTest(unittest.TestCase):
    """SDL-through-ACES gate + flag-placement cross-check (issue #84, ADR 0011).

    SDL is validated through the real ACES parser (a hard, pinned dependency),
    never a local schema. These drive the gate over temp catalogs using the same
    ``CI.SCEN``/``CI._REPO`` repointing pattern as the other gate-infra tests.
    """

    def _pack(self, *, sdl: dict[str, str] | None, placement: str | None = None):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        scen = os.path.join(tmp, "scenarios")
        pack = os.path.join(scen, "example-pack")
        sdl_dir = os.path.join(pack, "sdl")
        os.makedirs(sdl_dir, exist_ok=True)
        with open(os.path.join(pack, "pack.yaml"), "w", encoding="utf-8") as fh:
            fh.write(
                "name: example-pack\n"
                "title: Example Pack\n"
                "version: 0.1.0\n"
                "provenance_ledger: docs/provenance-ledger.yaml\n"
            )
        docs = os.path.join(pack, "docs")
        os.makedirs(docs, exist_ok=True)
        with open(os.path.join(docs, "provenance-ledger.yaml"), "w",
                  encoding="utf-8") as fh:
            yaml.safe_dump(_valid_ledger("example-pack"), fh)
        for name, body in (sdl or {}).items():
            with open(os.path.join(sdl_dir, name), "w", encoding="utf-8") as fh:
                fh.write(body)
        if placement is not None:
            flags = os.path.join(pack, "flags")
            os.makedirs(flags, exist_ok=True)
            with open(os.path.join(flags, "placement.yaml"), "w",
                      encoding="utf-8") as fh:
                fh.write(placement)
        return tmp, scen

    def _run(self, tmp, scen):
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        try:
            failures: list[str] = []
            views = CI.check_static_contract(failures)
            CI.check_sdl(failures, views)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo
        return failures

    def test_valid_sdl_with_resolved_placement_is_clean(self):
        placement = "flags:\n  - flag_id: mail\n    host: boreas-mail\n"
        tmp, scen = self._pack(sdl={"example.sdl.yaml": _VALID_SDL},
                               placement=placement)
        self.assertEqual(self._run(tmp, scen), [])

    def test_invalid_sdl_is_flagged(self):
        tmp, scen = self._pack(sdl={"example.sdl.yaml": _INVALID_SDL})
        blob = "\n".join(self._run(tmp, scen))
        self.assertIn("SDL INVALID", blob)
        self.assertIn("example.sdl.yaml", blob)

    def test_invalid_sdl_diagnostic_is_bounded_and_pathless(self):
        # The bounded diagnostic must not leak the absolute temp path or dump an
        # unbounded payload (ADR 0011).
        tmp, scen = self._pack(sdl={"example.sdl.yaml": _INVALID_SDL})
        failures = self._run(tmp, scen)
        [invalid] = [f for f in failures if f.startswith("SDL INVALID")]
        self.assertNotIn(tmp, invalid)
        self.assertLess(len(invalid), 300)

    def test_missing_sdl_document_is_flagged(self):
        tmp, scen = self._pack(sdl=None)  # sdl/ exists but ships no *.sdl.yaml
        blob = "\n".join(self._run(tmp, scen))
        self.assertIn("SDL MISSING", blob)

    def test_flag_host_absent_from_sdl_is_flagged(self):
        placement = "flags:\n  - flag_id: mail\n    host: ghost-host\n"
        tmp, scen = self._pack(sdl={"example.sdl.yaml": _VALID_SDL},
                               placement=placement)
        blob = "\n".join(self._run(tmp, scen))
        self.assertIn("FLAG PLACEMENT INVALID", blob)
        self.assertIn("ghost-host", blob)

    def test_host_resolves_against_union_of_variants(self):
        # A host present in only one validated variant resolves (union rule).
        variant = "\n".join([
            "name: example-pack", "nodes:", "  brain-controller:",
            "    type: vm", ""])
        placement = "flags:\n  - flag_id: mail\n    host: brain-controller\n"
        tmp, scen = self._pack(
            sdl={"example.sdl.yaml": _VALID_SDL, "example-demo.sdl.yaml": variant},
            placement=placement)
        self.assertEqual(self._run(tmp, scen), [])

    def test_empty_placement_is_clean(self):
        tmp, scen = self._pack(sdl={"example.sdl.yaml": _VALID_SDL},
                               placement="flags: []\n")
        self.assertEqual(self._run(tmp, scen), [])

    def test_author_adapters_share_one_static_validation_snapshot(self):
        tmp, scen = self._pack(sdl={"example.sdl.yaml": _VALID_SDL})
        orig_scen, orig_repo = CI.SCEN, CI._REPO
        CI.SCEN, CI._REPO = scen, tmp
        CI._AUTHOR_STATIC_CACHE.clear()
        try:
            failures: list[str] = []
            with mock.patch.object(
                CI,
                "_validate_pack_for_author_ci",
                wraps=CI._validate_pack_for_author_ci,
            ) as validator:
                views = CI.check_static_contract(failures)
                CI.check_sdl(failures, views)
                CI.check_manifest(failures, views)
                CI.check_provenance(failures, views)
            self.assertEqual(validator.call_count, 1)
            self.assertEqual(failures, [])
            self.assertTrue(views["example-pack"].scenarios)
        finally:
            CI.SCEN, CI._REPO = orig_scen, orig_repo

    def test_node_id_extraction_reads_scenario_nodes(self):
        class _FakeScenario:
            nodes = {"a": object(), "b": object()}
        self.assertEqual(CI._sdl_node_ids(_FakeScenario()), {"a", "b"})
        self.assertEqual(CI._sdl_node_ids(object()), set())

    def test_symlinked_sdl_escaping_pack_root_is_rejected(self):
        # A symlinked sdl/*.sdl.yaml whose real target lives outside the pack
        # root must be rejected by the real-path guard, without ACES ever
        # following the link into a parse (ADR 0011 containment discipline).
        tmp, scen = self._pack(sdl={"example.sdl.yaml": _VALID_SDL})
        outside = os.path.join(tmp, "outside.sdl.yaml")
        with open(outside, "w", encoding="utf-8") as fh:
            fh.write(_VALID_SDL)  # valid, so only the guard can produce a failure
        link = os.path.join(scen, "example-pack", "sdl", "escape.sdl.yaml")
        os.symlink(outside, link)

        blob = "\n".join(self._run(tmp, scen))
        self.assertIn("PACK STATIC INVALID", blob)

    def test_missing_aces_sdl_dependency_fails_closed(self):
        # A broken environment where the pinned dep is unimportable is a
        # fail-closed gate failure, never a silent skip (ADR 0011).
        def _boom():
            raise ImportError("no module named 'aces_sdl'")

        orig = CI._load_aces_sdl
        CI._load_aces_sdl = _boom
        try:
            failures: list[str] = []
            CI.check_sdl(failures)
        finally:
            CI._load_aces_sdl = orig
        self.assertIn("SDL VALIDATION UNAVAILABLE", "\n".join(failures))


class ChallengeCategoryPartitionTest(unittest.TestCase):
    """The shared `challenges.category.forbidden` code renders in author CI."""

    def test_challenge_code_is_partitioned_as_challenge_failure(self):
        g: list[str] = []
        m: list[str] = []
        p: list[str] = []
        s: list[str] = []
        CI._partition_author_static_error(
            "testpack",
            "challenges.category.forbidden: "
            "challenges/challenges.yaml:challenges[0].category",
            g, m, p, s)
        self.assertEqual((m, p, s), ([], [], []))
        self.assertTrue(any("CHALLENGE INVALID" in line for line in g), g)


if __name__ == "__main__":
    unittest.main()
