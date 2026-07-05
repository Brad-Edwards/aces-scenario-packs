"""Tests for the shared ACES oracle model.

The fixtures are representative contracts, not replacements for pack-local
oracle ledgers. They prove the reusable shape can express the current APT29,
FIN7/Carbanak, Wizard Spider, and Scattered Spider structures.
"""

from __future__ import annotations

import copy
import importlib.util
import os
import unittest

import yaml

_PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "aces_scenario_packs")
_MODEL_PATH = os.path.join(_PKG, "oracle_model.py")
_FIXTURE_DIR = os.path.join(_PKG, "resources", "oracle", "fixtures")


def _load_model_module():
    spec = importlib.util.spec_from_file_location("oracle_model_undertest", _MODEL_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


OM = _load_model_module()


def _fixture_path(name: str) -> str:
    return os.path.join(_FIXTURE_DIR, f"{name}.yaml")


def _load_fixture(name: str) -> dict:
    with open(_fixture_path(name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _issue_invariants(issues) -> set[str]:
    return {issue.invariant for issue in issues}


class FixtureValidationTests(unittest.TestCase):
    FIXTURES = ("apt29", "fin7-carbanak", "wizard-spider", "scattered-spider")

    def test_required_adversary_fixtures_validate(self):
        for name in self.FIXTURES:
            with self.subTest(fixture=name):
                issues = OM.validate(_load_fixture(name), source=_fixture_path(name))
                self.assertEqual([str(i) for i in issues], [])

    def test_ctfd_is_not_the_only_consumer(self):
        for name in self.FIXTURES:
            data = _load_fixture(name)
            consumer_types = {row["type"] for row in data["consumers"]}
            with self.subTest(fixture=name):
                self.assertIn("ctfd", consumer_types)
                self.assertTrue(consumer_types - {"ctfd"})

    def test_alternate_awards_are_explicit_and_reviewable(self):
        saw_alternate = False
        for name in self.FIXTURES:
            data = _load_fixture(name)
            for alt in data.get("accepted_alternates", []):
                saw_alternate = True
                with self.subTest(fixture=name, alternate=alt["id"]):
                    self.assertEqual(alt["review"]["status"], "explicit")
                    self.assertIn("outcome", alt["award"])
                    self.assertGreaterEqual(alt["award"]["points"], 0)
                    self.assertTrue(alt["predicate"].strip())
                    self.assertTrue(alt["evidence"])
        self.assertTrue(saw_alternate, "fixtures should exercise alternate awards")

    def test_exports_cover_operator_debrief_and_agent_benchmark(self):
        for name in self.FIXTURES:
            data = _load_fixture(name)
            audiences = {row["audience"] for row in data["exports"]}
            with self.subTest(fixture=name):
                self.assertIn("operator_debrief", audiences)
                self.assertIn("agent_benchmark", audiences)

                debrief = OM.render_export(data, "operator_debrief")
                benchmark = OM.render_export(data, "agent_benchmark")
                self.assertIn("accepted_alternates", debrief)
                self.assertIn("outcomes", benchmark)
                self.assertNotIn("path_steps", benchmark)
                self.assertNotIn("accepted_alternates", benchmark)
                self.assertNotIn("success_state", repr(benchmark))
                self.assertNotIn("predicate", repr(benchmark))


class ValidationFailureTests(unittest.TestCase):
    def test_mutating_evidence_is_rejected(self):
        data = _load_fixture("apt29")
        bad = copy.deepcopy(data)
        bad["path_steps"][0]["required_evidence"][0]["mutates_scenario_state"] = True

        issues = OM.validate(bad, source="mutating-fixture")

        self.assertIn("idempotent_validator", _issue_invariants(issues))

    def test_oracle_and_participant_roots_must_be_separate(self):
        data = _load_fixture("apt29")
        bad = copy.deepcopy(data)
        bad["visibility"]["participant_roots"] = [{"path": "oracle/"}]
        bad["visibility"]["oracle_roots"] = [{"path": "oracle/private.yaml"}]

        issues = OM.validate(bad, source="overlap-fixture")

        self.assertIn("visibility_overlap", _issue_invariants(issues))

    def test_backslash_path_escape_is_rejected(self):
        data = _load_fixture("apt29")
        bad = copy.deepcopy(data)
        bad["visibility"]["oracle_roots"] = [{"path": "..\\private.yaml"}]

        issues = OM.validate(bad, source="backslash-escape-fixture")

        self.assertIn("path_escape", _issue_invariants(issues))

    def test_alternate_without_explicit_review_is_rejected(self):
        data = _load_fixture("fin7-carbanak")
        bad = copy.deepcopy(data)
        bad["accepted_alternates"][0]["review"]["status"] = "implicit"

        issues = OM.validate(bad, source="implicit-alt-fixture")

        self.assertIn("alternate_review", _issue_invariants(issues))

    def test_ctfd_only_consumer_is_rejected(self):
        data = _load_fixture("apt29")
        bad = copy.deepcopy(data)
        bad["consumers"] = [row for row in bad["consumers"] if row["type"] == "ctfd"]

        issues = OM.validate(bad, source="ctfd-only-fixture")

        self.assertIn("consumer_independence", _issue_invariants(issues))

    def test_unsafe_proof_field_is_rejected(self):
        data = _load_fixture("wizard-spider")
        bad = copy.deepcopy(data)
        bad["path_steps"][0]["required_evidence"][0]["proof_fields"].append(
            "raw_credential"
        )

        issues = OM.validate(bad, source="unsafe-proof-fixture")

        self.assertIn("unsafe_proof_field", _issue_invariants(issues))

    def test_unresolved_award_target_is_rejected(self):
        data = _load_fixture("scattered-spider")
        bad = copy.deepcopy(data)
        bad["accepted_alternates"][0]["award"]["outcome"] = "missing-outcome"

        issues = OM.validate(bad, source="bad-award-fixture")

        self.assertIn("unresolved_ref", _issue_invariants(issues))


if __name__ == "__main__":
    unittest.main()
