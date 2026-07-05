# ADR 0007 — Changelog-driven versioning

- Status: Accepted
- Date: 2026-07-06
- Supersedes: the **versioning mechanism** of
  [ADR 0006](0006-conventional-commit-releases.md). ADR 0006's other decisions
  (hatch-vcs tag-derived build version, protected-`main` / tag-only release, SBOM,
  PyPI OIDC, the PR-title guard, squash-feature / merge-promotion) still hold.

> **Reusable blueprint.** Portable to other repos; only the package name and
> branch names are repo-specific.

## Context

ADR 0006 computed the version from **Conventional Commit messages** (via
python-semantic-release) while the human `CHANGELOG.md` was maintained separately
with **towncrier fragments**. That is two independent sources for one release:
the tool could tag `0.2.0` from a `feat:` commit while the changelog section said
`0.1.0`. The version and the changelog could **drift**.

## Decision

Make the **changelog the single source of the version**. The towncrier fragments
decide both what the release notes say *and* how big the version bump is, so the
tag is a pure function of the changelog and cannot drift from it.

### 1. The fragment type is the bump

`changelog.d/<issue>.<type>.md`; the highest-severity type accumulated since the
last release decides the bump:

| Fragment type | Bump |
|---|---|
| `breaking`, `removed` | major |
| `added`, `changed`, `deprecated` | minor |
| `security`, `fixed` | patch |

Pre-1.0 (`0.y.z`): a major-level change bumps the **minor** (SemVer 0.x rule). A
`breaking` fragment type exists precisely so majors are explicit — Keep-a-Changelog
categories alone don't unambiguously signal a breaking change.

`tools/release_bump.py` is the single implementation: `next` (compute from
fragments + last tag), `current` (read `CHANGELOG.md`'s newest `## [X.Y.Z]`), and
`notes` (that section's body). It has no commit-message input.

### 2. `CHANGELOG.md`'s newest section IS the release version

Cutting a release writes the version into `CHANGELOG.md` (via towncrier), and the
release reads it back from there and tags it. One number, one source.

### 3. Two workflows, `main` stays protected

- **Prepare release** (`workflow_dispatch`): computes the next version from the
  fragments, runs `towncrier build --version <that>`, and opens a `release/vX.Y.Z`
  PR into `dev`. This is the deliberate "cut a release" action.
- **Release** (`on: push: main`): first, a **guard** — if typed fragments are
  still pending (Prepare Release hasn't collated them), it **skips**, so a stale
  changelog can never be published regardless of promotion order. Otherwise it
  reads `CHANGELOG.md`'s newest version; if it has no tag yet, it **creates the
  tag** (`refs/tags/*` is not branch-protected — no commit is ever pushed to
  `main`), builds the sdist + wheel (hatch-vcs derives the version from the tag),
  **asserts the built version equals the changelog version** (final anti-drift
  check), attaches a CycloneDX SBOM, publishes to PyPI via OIDC, and cuts a GitHub
  Release whose notes are the changelog section.

The first release is not special: there is no seed and no manual tag — you run
Prepare Release for `0.1.0` exactly as for every later version.

So: fragments → (prepare) `CHANGELOG.md [X.Y.Z]` → (release) tag `vX.Y.Z` → build
version `X.Y.Z`. Every step reads the same number; drift is impossible by
construction.

## The two vocabularies (don't confuse them)

- **Changelog fragment types** (`added`/`fixed`/`breaking`/…) → decide the
  **version**.
- **Conventional PR titles** (`feat:`/`fix:`/…, enforced by the PR-title guard) →
  keep the git history tidy and ban agent-branding prefixes. They no longer drive
  the version.

## Consequences

- The version and `CHANGELOG.md` cannot drift — the version is derived from the
  changelog.
- Releasing is a deliberate act (run "Prepare release"), which matches towncrier's
  model; there is no accidental auto-release from an unrelated merge.
- Every user-visible change must add a fragment, or it won't appear in the
  changelog or move the version. Repo-internal changes (CI, tests, refactors)
  add none and don't release.
- `main` stays protected; the release only ever pushes a tag.
