# ADR 0007 — Changelog-driven versioning (committed literal)

- Status: Accepted
- Date: 2026-07-06
- Supersedes: the **versioning + release mechanism** of
  [ADR 0006](0006-conventional-commit-releases.md). ADR 0006's other decisions
  (SBOM, PyPI OIDC, the PR-title guard, protected `main`) still hold.

> **Reusable blueprint.** Portable across repos; per-repo variables:
> `{{DIST}}` = PyPI name, `{{VERSION_FILE}}` = the package `__init__.py`,
> `{{REPO}}` = `owner/repo`. For this repo: `aces-scenario-packs`,
> `src/aces_scenario_packs/__init__.py`, `Brad-Edwards/aces-scenario-packs`.

## Context

The version and the changelog must never disagree. Earlier attempts derived the
version from git tags (hatch-vcs) or commit messages (semantic-release), kept the
changelog separately, and needed special first-release seeding. Too many moving
parts, and drift was possible.

## Decision

**One committed literal is the version; the changelog decides the bump.**

### 1. Version = one committed literal
`{{VERSION_FILE}}` contains exactly `__version__ = "X.Y.Z"`. `pyproject.toml`
declares `dynamic = ["version"]` and `[tool.hatch.version] path = "{{VERSION_FILE}}"`
so hatchling reads that literal. No hatch-vcs, no setuptools-scm, no
semantic-release, no static `[project].version`.

### 2. Changelog = towncrier
Per PR, add `changelog.d/<slug>.<type>.md` (types: `breaking`, `security`,
`added`, `changed`, `deprecated`, `removed`, `fixed`). Never edit `CHANGELOG.md`
directly.

### 3. `tools/release.py` cuts a release
It computes the next version from the pending fragment **types** (rubric below),
writes it into `{{VERSION_FILE}}`, and runs `towncrier build` (which writes the
`CHANGELOG.md` section and consumes the fragments). No git ops — you commit on a
`release/vX.Y.Z` branch and open a PR to `main`.

### 4. `release.yml` (on push to `main`)
- **decide**: **skip if any typed fragment is still uncollated** (a real release
  collates first via `tools/release.py`; this blocks the first `main` promotion
  from publishing before a release is cut). Otherwise read `__version__`; release
  only if it has **no `vX.Y.Z` tag** and a matching `## [X.Y.Z]` section exists in
  `CHANGELOG.md` (so an un-changelogged version, including the unreleased `0.0.0`,
  never ships).
- **release** (`environment: pypi`, `contents: write` + `id-token: write`): create
  and push the `vX.Y.Z` tag, build sdist + wheel, generate the SBOM, extract the
  `## [X.Y.Z]` changelog section as the notes, publish to PyPI via OIDC, and cut
  the GitHub Release. **Only a tag is pushed — never a commit to `main`**, so no
  bot/PAT/deploy-key/bypass is needed. Third-party actions are SHA-pinned.

### 5. Rubric
Pre-1.0 (`major == 0`): any `added`/`changed`/`removed`/`deprecated`/`breaking` →
minor; `fixed`/`security` → patch. `major >= 1`: `removed`/`breaking` → major,
`added`/`changed`/`deprecated` → minor, `fixed`/`security` → patch. (`breaking` is
effectively capped to minor until you cut 1.0.)

### 6. One-time per repo (owner)
Register a PyPI trusted publisher (project `{{DIST}}`, owner, repo, workflow
`release.yml`, environment `pypi`) and create a GitHub environment named `pypi`.

## Release flow
`python tools/release.py` → `release/vX.Y.Z` branch → PR to `main` → merge →
`release.yml` tags and publishes. The **first release is not special** — you run
`tools/release.py` for `0.1.0` exactly as for every later version. For dependent
repos, publish the dependency first (e.g. `aces-sdl` before `aptl`).

## Consequences
- The version is one literal; the build, the tag, and the changelog all read the
  same number — drift is structurally impossible.
- No seeding, no pre-tag, no bypass; `main` only ever receives a tag.
- Every user-visible change must add a fragment or it neither appears in the
  changelog nor moves the version.
