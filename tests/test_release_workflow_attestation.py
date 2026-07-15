"""Static workflow-contract guard for release build-provenance attestation.

ADR 0015 requires the release ``publish`` job to attest the wheel and sdist it
builds with GitHub's SLSA build-provenance action, before either publication
destination (PyPI, GitHub Release), so every released artifact is verifiable
with ``gh attestation verify``. These are static checks: the acceptance
contract (a real ``gh attestation verify`` pass) can only be met by an actual
release run, but the workflow shape that produces it is guarded here so a
reorder, an unpinned action, or a dropped permission fails CI.

Scope is deliberately narrow — the release workflow's attestation contract
only. It reuses the repo's existing unittest + PyYAML stack rather than adding
a new validation framework.
"""

from __future__ import annotations

import pathlib
import re
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "release-please.yml"

_ATTEST_ACTION = "actions/attest-build-provenance@"
_PYPI_ACTION = "pypa/gh-action-pypi-publish@"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _load_publish_job() -> dict:
    data = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return data["jobs"]["publish"]


class ReleaseAttestationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.publish = _load_publish_job()
        self.steps = self.publish["steps"]

    def _index(self, predicate) -> int:
        for index, step in enumerate(self.steps):
            if predicate(step):
                return index
        return -1

    def _attest_step(self) -> dict:
        for step in self.steps:
            if str(step.get("uses", "")).startswith(_ATTEST_ACTION):
                return step
        self.fail("release publish job has no actions/attest-build-provenance step")

    def test_attest_step_is_present_and_sha_pinned(self) -> None:
        uses = self._attest_step()["uses"]
        ref = uses.split("@", 1)[1].split()[0]
        self.assertRegex(
            ref,
            _SHA_RE,
            "attest-build-provenance must be pinned to a 40-hex commit SHA, "
            f"not a floating tag/branch: {uses!r}",
        )

    def test_publish_job_grants_attestations_write_and_keeps_oidc(self) -> None:
        permissions = self.publish.get("permissions", {})
        self.assertEqual(permissions.get("attestations"), "write",
                         "publish job must grant attestations: write (ADR 0015)")
        # The signing identity and Release upload must survive alongside it.
        self.assertEqual(permissions.get("id-token"), "write",
                         "publish job must keep id-token: write for OIDC/Sigstore")
        self.assertEqual(permissions.get("contents"), "write",
                         "publish job must keep contents: write for Release upload")

    def test_subject_path_covers_wheel_and_sdist(self) -> None:
        subject_path = self._attest_step().get("with", {}).get("subject-path")
        self.assertIsNotNone(subject_path, "attest step must set subject-path")
        if isinstance(subject_path, list):
            subject_path = "\n".join(subject_path)
        self.assertIn("*.whl", subject_path, "attestation must cover the wheel")
        self.assertIn("*.tar.gz", subject_path, "attestation must cover the sdist")

    def test_attestation_runs_before_publication_destinations(self) -> None:
        build = self._index(
            lambda s: "-m build" in str(s.get("run", "")))
        attest = self._index(
            lambda s: str(s.get("uses", "")).startswith(_ATTEST_ACTION))
        pypi = self._index(
            lambda s: str(s.get("uses", "")).startswith(_PYPI_ACTION))
        release_upload = self._index(
            lambda s: "gh release upload" in str(s.get("run", "")))

        for name, idx in (("build", build), ("attest", attest),
                          ("pypi publish", pypi), ("release upload", release_upload)):
            self.assertGreaterEqual(idx, 0, f"could not locate the {name} step")

        self.assertLess(build, attest, "attestation must run after the artifacts are built")
        self.assertLess(attest, pypi, "attestation must run before PyPI publication")
        self.assertLess(attest, release_upload,
                        "attestation must run before the GitHub Release upload")


if __name__ == "__main__":
    unittest.main()
