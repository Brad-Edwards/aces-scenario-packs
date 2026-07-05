# ADR 0003 — Build and release model

- Status: Accepted
- Date: 2026-07-05

## Context

ADR 0002 makes this repository a published package. Publishing needs a
repeatable, auditable build and release process that does not depend on
long-lived credentials and that produces artifacts consumers can pin.

## Decision

- **Build backend:** `pyproject.toml` (PEP 621 metadata) with **hatchling**.
  Runtime dependency: `PyYAML`. Package data (schemas, template, oracle, contract
  version) is declared so it ships in the sdist and wheel.
- **Versioning:** the package uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`).
  This is distinct from the pack **contract version** (a separate integer +
  digest the package carries and the tools enforce); a package release notes
  which contract version it ships. Pre-1.0 (`0.y.z`) makes no
  backward-compatibility promise.
- **Console entry points:** `aces-pack-validate`, `aces-pack-release`,
  `aces-new-pack`, `aces-pack-issue-skeleton`.
- **Changelog:** fragment-based via `changelog.d/` (towncrier categories),
  collated into `CHANGELOG.md` at release time. No direct `CHANGELOG.md` edits.
- **Release trigger:** pushing a `v<MAJOR>.<MINOR>.<PATCH>` tag runs the release
  workflow, which builds the sdist + wheel, generates the SBOM (ADR 0004),
  publishes to **PyPI via OpenID Connect trusted publishing** (no API tokens
  stored in the repository), and cuts a **GitHub Release** carrying the wheel,
  sdist, and SBOM.
- **CI (every PR/push):** runs the unit tests and the content/release gates
  (`aces-pack-validate`, `aces-pack-release check --all`) so `main`/`dev` stay
  releasable. Releases are cut from `main`.

## Consequences

- No secret PyPI token lives in the repository; publish authorization is the
  OIDC trust relationship between GitHub and PyPI.
- A release is reproducible from a tag and leaves a durable, downloadable record
  (GitHub Release + PyPI) with the SBOM attached.
- Consumers pin `aces-scenario-packs==X.Y.Z` (or a compatible range) and upgrade
  deliberately.
