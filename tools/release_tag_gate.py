#!/usr/bin/env python3
"""Release-tag signing gate for the canonical release workflow.

Single source of truth for the release-detection, config-validation, and
release-notes logic used by ``.github/workflows/release-please.yml``. Release
Please runs in PR-only mode (``skip-github-release: true``); this gate decides
whether a push to ``main`` is a *release transition* — the Release Please-owned
``[project].version`` change — so the workflow can create, sign, and verify a
tag itself (ADR 0017). Mirrors the ``tools/check_pr_title.py`` seam: the workflow
and ``tests/test_release_tag_gate.py`` call the same pure functions, so policy
cannot drift between YAML and local enforcement.

Design:
  * Authorization is bound to an *authenticated* Release Please signal, not to a
    raw version bump: a push publishes only when the merged pull request carries
    Release Please's ``autorelease: pending`` label (which only Release Please
    applies to its own release PRs). A feature PR that merely edits
    ``[project].version`` cannot forge that label, so it cannot authorize a
    signed tag or a PyPI publish (ADR 0017 security binding). The version /
    manifest parsing below is a *consistency check* layered on top, never the
    authorization by itself.
  * TOML / JSON are parsed with their real parsers (``tomllib`` / ``json``),
    never sourced or scraped with shell text matching (ADR 0017).
  * Commit revisions cross into a subprocess only after 40-hex shape validation;
    no value is ever evaluated as shell code, and nothing runs through a shell.
  * Fail-closed: an unauthorized push is a clean no-release; a version that
    changed but is malformed (non-stable-SemVer, or a manifest that disagrees)
    raises rather than silently releasing or silently skipping.

Stdlib-only so the CI job runs on a bare ``python`` interpreter (Python >= 3.11
for ``tomllib``).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass

#: A stable release version: MAJOR.MINOR.PATCH with no pre-release/build metadata.
_STABLE_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

#: A full git object SHA (lowercase hex, 40 chars). ``github.sha`` is this shape.
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

#: The all-zero SHA git/GitHub uses for "no prior revision" (branch create, etc.).
_NULL_SHA = "0" * 40

#: The tag prefix Release Please emits (``include-v-in-tag`` defaults true).
_TAG_PREFIX = "v"

#: The label Release Please puts on its own release PRs. Its presence on the
#: merged PR is the authenticated signal that this push is the admin-gated
#: release act — not an arbitrary version edit (ADR 0017 security binding).
RELEASE_PR_LABEL = "autorelease: pending"

_PYPROJECT_PATH = "pyproject.toml"
_MANIFEST_PATH = ".release-please-manifest.json"
_ROOT_PACKAGE = "."


class GateError(Exception):
    """A release-gate validation failure. Callers exit non-zero (fail-closed)."""


@dataclass(frozen=True)
class ReleaseDecision:
    """Outcome of release detection for a single push."""

    release: bool
    version: str | None = None
    tag: str | None = None


def parse_project_version(pyproject_text: str) -> str:
    """Return ``[project].version`` from ``pyproject.toml`` text.

    Raises ``GateError`` on a parse failure or a missing version.
    """
    try:
        data = tomllib.loads(pyproject_text)
    except tomllib.TOMLDecodeError as exc:
        raise GateError(f"pyproject.toml is not valid TOML: {exc}") from exc
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise GateError("pyproject.toml has no [project].version string")
    return version


def is_stable_semver(version: str) -> bool:
    """True iff ``version`` is a strict stable ``MAJOR.MINOR.PATCH``."""
    return bool(_STABLE_SEMVER_RE.match(version))


def is_release_authorized(
    labels: Sequence[str], *, required_label: str = RELEASE_PR_LABEL
) -> bool:
    """True iff the merged PR carries Release Please's release-PR label.

    This is the authorization signal: only Release Please applies
    ``autorelease: pending`` to its own release PRs, so an arbitrary feature PR
    that edits the version cannot forge it. Absence of the label (including an
    empty list) is a fail-closed no-release.
    """
    return required_label in set(labels)


def validate_manifest(manifest_text: str, expected_version: str) -> None:
    """Validate ``.release-please-manifest.json`` shape and version.

    The manifest must contain exactly the root package entry (``.``) and its
    value must equal ``expected_version``. Raises ``GateError`` otherwise.
    """
    try:
        data = json.loads(manifest_text)
    except json.JSONDecodeError as exc:
        raise GateError(f".release-please-manifest.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {_ROOT_PACKAGE}:
        raise GateError(
            ".release-please-manifest.json must contain exactly the root "
            f"package entry {_ROOT_PACKAGE!r}; got keys {sorted(data)!r}"
        )
    if data[_ROOT_PACKAGE] != expected_version:
        raise GateError(
            "manifest version "
            f"{data[_ROOT_PACKAGE]!r} != pyproject version {expected_version!r}"
        )


def expected_tag(version: str) -> str:
    """The tag Release Please would have created for ``version``."""
    return f"{_TAG_PREFIX}{version}"


def detect_release(
    before_pyproject: str | None,
    after_pyproject: str,
    after_manifest: str,
) -> ReleaseDecision:
    """Decide whether a push is a release transition.

    A release is the Release Please-owned ``[project].version`` change reaching
    the branch. When the version changed, the new version must be a strict stable
    SemVer and the manifest must agree — otherwise this fails closed
    (``GateError``) rather than releasing something malformed. A push with no
    prior revision, or with an unchanged version, is a clean no-release.
    """
    if before_pyproject is None:
        return ReleaseDecision(release=False)

    before_version = parse_project_version(before_pyproject)
    after_version = parse_project_version(after_pyproject)
    if before_version == after_version:
        return ReleaseDecision(release=False)

    if not is_stable_semver(after_version):
        raise GateError(
            f"release version {after_version!r} is not a strict stable SemVer"
        )
    validate_manifest(after_manifest, after_version)
    return ReleaseDecision(
        release=True, version=after_version, tag=expected_tag(after_version)
    )


def extract_release_notes(changelog_text: str, version: str) -> str:
    """Return the body of ``changelog_text``'s section for ``version``.

    Matches the Release Please heading ``## [<version>](...) (...)`` exactly
    (so ``2.0.1`` is not satisfied by a ``2.0.10`` heading) and returns the text
    up to the next ``## `` heading, excluding the version heading line itself.
    Raises ``GateError`` if the section is absent.
    """
    heading_re = re.compile(rf"^## \[{re.escape(version)}\]")
    lines = changelog_text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if heading_re.match(line):
            start = index + 1
            break
    if start is None:
        raise GateError(f"CHANGELOG.md has no section for version {version!r}")
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)
    notes = "\n".join(body).strip()
    if not notes:
        raise GateError(f"CHANGELOG.md section for {version!r} is empty")
    return notes


def _git_show(sha: str, path: str) -> str:
    """Return the contents of ``path`` at revision ``sha``.

    ``sha`` is shape-validated to 40-hex before it reaches the subprocess, and
    the command is run without a shell, so nothing crosses into shell code.
    """
    if not _SHA_RE.match(sha):
        raise GateError(f"refusing to read a non-SHA revision: {sha!r}")
    result = subprocess.run(
        ["git", "show", f"{sha}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GateError(f"git show {sha}:{path} failed: {result.stderr.strip()}")
    return result.stdout


def _read_labels(path: str | None) -> list[str]:
    """Read one-label-per-line from ``path``; missing/empty file → no labels."""
    if not path:
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.strip()]
    except OSError:
        return []


def _cmd_check(args: argparse.Namespace) -> int:
    # Authorization first: without the authenticated Release Please label this
    # push is not a release, regardless of any version change (fail closed).
    labels = _read_labels(args.merged_pr_labels_file)
    if not is_release_authorized(labels):
        _emit_outputs(args.github_output, ["release=false"])
        print("release-tag-gate: release=false (no authenticated release-PR label)")
        return 0

    after = args.after
    if not _SHA_RE.match(after):
        raise GateError(f"--after must be a 40-hex commit SHA; got {after!r}")

    before = args.before
    if before == _NULL_SHA or not _SHA_RE.match(before):
        # No trustworthy prior revision to diff against: cannot be a transition.
        before_pyproject = None
    else:
        before_pyproject = _git_show(before, _PYPROJECT_PATH)

    after_pyproject = _git_show(after, _PYPROJECT_PATH)
    after_manifest = (
        _git_show(after, _MANIFEST_PATH) if before_pyproject is not None else "{}"
    )
    decision = detect_release(before_pyproject, after_pyproject, after_manifest)

    lines = [f"release={'true' if decision.release else 'false'}"]
    if decision.release:
        lines.append(f"tag={decision.tag}")
        lines.append(f"version={decision.version}")
    _emit_outputs(args.github_output, lines)
    print(f"release-tag-gate: {' '.join(lines)}")
    return 0


def _cmd_notes(args: argparse.Namespace) -> int:
    with open(args.changelog, encoding="utf-8") as handle:
        changelog_text = handle.read()
    notes = extract_release_notes(changelog_text, args.version)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(notes + "\n")
    print(f"release-tag-gate: wrote notes for {args.version} to {args.output}")
    return 0


def _emit_outputs(github_output: str | None, lines: Sequence[str]) -> None:
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Release-tag signing gate.")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="detect an authorized release on a push")
    check.add_argument("--before", required=True, help="github.event.before SHA")
    check.add_argument("--after", required=True, help="github.sha SHA")
    check.add_argument("--merged-pr-labels-file", default=None,
                       help="file of merged-PR label names, one per line; absent "
                            "or lacking the release-PR label means no release")
    check.add_argument("--github-output", default=None,
                       help="path to append key=value outputs (defaults to none)")
    check.set_defaults(func=_cmd_check)

    notes = sub.add_parser("notes", help="extract the CHANGELOG section for a version")
    notes.add_argument("--version", required=True, help="the release version (X.Y.Z)")
    notes.add_argument("--changelog", required=True, help="path to CHANGELOG.md")
    notes.add_argument("--output", required=True, help="path to write the notes file")
    notes.set_defaults(func=_cmd_notes)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except GateError as exc:
        print(f"release-tag-gate: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
