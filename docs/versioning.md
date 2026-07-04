# Versioning and Release Policy

This page records how the ACES scenario-pack companion repository versions and
releases its public artifacts. It is policy only. Static pack validation and
release-record checks have landed in [`../tools/`](../tools/README.md)
(Brad-Edwards/aces-scenario-packs#5); release *automation* that cuts tags or
publishes releases is tracked separately and is not implemented yet.

## Current status

The repository is a planning and migration scaffold. No scenario-pack contract,
schemas, tools, or example packs have shipped, so no version has been released.
Until the first contract lands, the repository is treated as pre-1.0 and any
published surface may change without a compatibility guarantee.

## Versioning scheme

- Published artifacts (the scenario-pack contract and its schemas) will use
  [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.
  - MAJOR: a breaking change to the pack contract or a published schema.
  - MINOR: a backward-compatible addition to the contract or a schema.
  - PATCH: a backward-compatible fix or clarification with no contract change.
- Schemas carry their own version metadata so a pack can declare the contract
  version it targets. The schema index is the source of truth for which schema
  versions are published.
- Pre-1.0 (`0.y.z`) releases make no backward-compatibility promise; a MINOR
  bump may break consumers while the contract stabilises.

## Release policy

- Releases are cut from `main` and tagged `vMAJOR.MINOR.PATCH`.
- A release records what changed, the compatibility impact, and the migration
  story for any breaking change, consistent with `CONTRIBUTING.md`.
- Changes reach `main` only through the reviewed branch flow recorded in
  [branch-protection.md](branch-protection.md); a release never bypasses it.
- A change that alters a published schema must also update the schema index and
  ship a loadable validation fixture (see `.gc/plan-rules.md`).

## Change tracking

Notable changes are recorded as fragments under
[`../changelog.d/`](../changelog.d/README.md) using the Keep a Changelog
categories, to be collated into a release changelog when release automation
lands. The static release-record check in [`../tools/`](../tools/README.md)
validates a pack's `release` record and cross-checks its declared schema versions
against the schema index.
