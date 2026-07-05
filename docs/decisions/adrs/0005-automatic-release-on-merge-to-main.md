# ADR 0005 — Automatic release on merge to main

- Status: Accepted
- Date: 2026-07-05
- Amends: [ADR 0003](0003-build-and-release-model.md) (release trigger and versioning source)

## Context

ADR 0003 established a tag-triggered release: a human pushes a `v<X.Y.Z>` tag and
the workflow builds, generates the SBOM, publishes to PyPI, and cuts a GitHub
Release. In practice the tag push is a manual, easy-to-forget step decoupled from
the change that actually warrants a release, and it invites tag/`__version__`
drift (a tag that doesn't match what shipped). We want a release to happen — be
created, tagged, and tracked in GitHub — automatically when release-worthy code
lands on `main`, with no separate ceremony.

ADR 0003 also left two version fields in `pyproject.toml`: a static
`[project].version` and a `[tool.hatch.version]` pointing at the package
`__init__.py`. That is two sources of truth for one value.

## Decision

- **Single version source of truth:** `__version__` in
  `src/aces_scenario_packs/__init__.py`. `[project].version` is declared
  `dynamic` and hatchling reads it from that module. The release workflow reads
  the same string. There is exactly one place to bump.
- **Primary release trigger — merge to `main`:** on push to `main`, the release
  workflow reads the packaged `__version__`. If no `v<version>` tag exists yet,
  it creates and pushes that annotated tag, then builds the sdist + wheel,
  generates the CycloneDX SBOM (ADR 0004), publishes to PyPI via OIDC trusted
  publishing, and cuts a GitHub Release carrying the wheel, sdist, and SBOM with
  auto-generated notes. If the tag already exists, the run is a no-op — so
  ordinary `main` pushes that don't bump the version do not release.
- **How you cut a release:** bump `__version__` in the PR (with the changelog
  fragment). Merging the PR to `main` is the release action. No manual tagging.
- **Manual `v*` tag push remains supported** as a backfill / re-run escape hatch;
  pushing a semver tag releases that exact ref. The single-workflow design means
  a merge-created tag and a hand-pushed tag follow the identical build/publish
  path and one PyPI trusted-publisher configuration (`release.yml`).
- **Tag authorship:** the merge-to-`main` path creates the tag with the workflow
  `GITHUB_TOKEN` from inside the release run itself, so no personal access token
  or downstream-trigger workaround is needed, and the token-created tag does not
  recursively re-trigger the workflow.

## Consequences

- A release is a consequence of merging, not a separate manual step; the tag
  always matches the shipped `__version__`.
- Forgetting to bump `__version__` means no release (safe default), not a
  mismatched or duplicate one; re-releasing a shipped version is prevented by the
  tag-exists check.
- The version lives in one file; the build and the release read the same value.
- Releasing still requires the OIDC trust relationship (ADR 0003) and the SBOM
  (ADR 0004); this ADR changes only *when* and *how* the release fires.
