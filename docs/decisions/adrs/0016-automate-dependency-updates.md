# ADR 0016 — Automate dependency updates and ship ACES bumps as releases

- Status: Accepted
- Date: 2026-07-16
- Extends: [ADR 0008](0008-adopt-release-please.md) and
  [ADR 0011](0011-require-pinned-aces-sdl-validation.md)

## Context

ADR 0011 makes `aces-sdl` an exactly pinned runtime dependency while the ACES
SDL contracts are `stability: draft`. That pin is correct, but keeping it moving
was expensive: the version was restated in three places Dependabot does not edit
— `pyproject.toml`, a unit test that hard-coded `aces-sdl==0.21.0`, and
`docs/scenario-packs.md` — so every bump was a multi-file manual edit. The doc
copy had already drifted (it still said `0.20.0` against a real pin of
`0.21.0`), which is the predictable failure mode of a hand-maintained mirror.

A version range would remove the mirror problem, but a range is only safe when
the upstream publishes a compatibility (semver) guarantee that a resolver can
rely on. ACES SDL is `0.x` and draft, so no such guarantee exists yet and
ADR 0011's exact pin stands. The problem to solve here is therefore the
*maintenance toil around the pin*, not the pin itself.

The compatibility gate needed to detect breaking ACES releases already exists:
CI's `verify` job installs the pinned `aces-sdl` and runs the unit tests, the
scenario-content gate (`aces-pack-validate`, which flows through
`aces_sdl.parse_sdl_file`), and the pack release gate. A breaking ACES release
turns `verify` red.

## Decision

The pinned version has one source of truth: `pyproject.toml`
`[project].dependencies`. Tests assert the exact-pin *invariant* — exactly one
`aces-sdl` requirement, pinned with `==` — rather than a literal version, so a
Dependabot bump stays green without a manual test edit. Prose and docs reference
`pyproject.toml` instead of restating the number. ADRs remain dated records and
are not version mirrors.

Dependabot opens weekly bump PRs against `dev`. GitHub Actions bumps and
non-`aces-sdl` runtime dependency bumps are auto-merged once the CI `verify`
gate is green (option A1). This removes the manual-edit toil for routine
patching.

`aces-sdl` is excluded from auto-merge. Advancing the pinned ACES dependency
stays a human-reviewed decision (ADR 0011): its compatibility gate runs
automatically on the Dependabot PR, but a person reviews the green, isolated
(ungrouped) PR and merges it. Auto-merge is not adopted for the load-bearing
pin.

Runtime dependency bumps (the `pip` ecosystem — `PyYAML` and `aces-sdl`) are
committed as `fix(deps)` so release-please cuts a patch release and consumers
receive the new floor through a normal `pip install -U`. GitHub Actions bumps
stay `chore` (CI-only; no release).

The auto-merge rail requires two settings outside the source tree: the repo
setting `allow_auto_merge`, and branch protection on `dev` requiring the
`verify` status check. The `sonar` check is deliberately **not** required — it
is skipped for Dependabot and fork PRs (no `SONAR_TOKEN`), and requiring a
conditionally-skipped check would deadlock auto-merge. `enforce_admins` stays
disabled so the release-please and `main → dev` back-merge PRs — opened with
`GITHUB_TOKEN`, which cannot trigger the required check — remain admin-mergeable,
as the sync workflow already anticipates.

## Consequences

- Routine dependency patching (Actions, `PyYAML`) merges with no human action
  when CI is green. The maintainer's only remaining ACES task is to review one
  green, isolated `aces-sdl` PR and merge it.
- Each accepted ACES bump ships as a patch release, so downstream packages track
  the ACES floor without waiting for an unrelated feature release.
- ADR 0011's exact-pin governance is unchanged. Loosening to a range remains
  available only after ACES publishes a stability/compatibility guarantee.
- Requiring `verify` on `dev` adds a green-CI gate to every PR into `dev`. The
  back-merge and release PRs continue to merge via admin override.
- Auto-merging `aces-sdl` itself (option A2) is a further decision that would
  have to amend ADR 0011 to declare the automated compatibility gate an accepted
  substitute for human review. This ADR does not.
