# ADR 0002: Scenario-Pack Validation and Release Tooling

Date: 2026-07-03

Status: Accepted

## Context

ASP-0005 is the issue that the scenario-pack contract, schema design guardrails,
and versioning policy defer validation and release tooling to. The repository now
publishes a normative contract and nine machine-readable schemas, but the only
executable enforcement was the internal `unittest` suite. An external pack author
had no reusable, offline way to check a pack against the published schemas, scan
it for leaked material, confirm a runtime profile is portable, or cross-check a
release record.

## Decision

Add a stdlib-only `tools/aces_pack_tools/` package that provides static, offline
pack checks behind a small `argparse` CLI (`validate`, `leak`, `release`),
following the [tooling design guardrails](../../tooling-design-guardrails.md):

- Schemas are resolved only through `schemas/index.json`; the tooling never
  hard-codes schema ids, versions, or fixtures, and never redefines ACES SDL
  semantics.
- The stdlib JSON Schema conformance checker that previously lived inside
  `tests/test_pack_schema_index.py` is promoted into `aces_pack_tools.schema` as
  the single source of truth; the test suite imports it rather than forking a
  second checker.
- A pack root is treated as untrusted input: paths resolve within the root and
  traversal or symlink escape is rejected.
- Findings are sanitized and actionable (check, pack-relative path, schema family
  or gate, concise reason) and never dump file contents, environment values, or
  credentials. Commands use ordinary exit codes (0 clean, 1 findings, 2 usage).
- The leak scanner ships no built-in vocabulary denylist; scrub terms are
  caller-supplied configuration, so the tool carries no downstream-private
  vocabulary itself.
- A consumer CI example under `examples/ci/` is runnable by external adopters
  with no secrets or private repository state.

## Consequences

- Pack authors get a repeatable, offline verification path before publishing or
  adopting a pack, satisfying ASP-0005.
- The conformance checker has one home; a schema keyword the checker cannot
  handle fails the existing coverage guard rather than passing silently.
- `validation.v0` remains evidence-only; the tooling can populate it later
  without that schema becoming responsible for running checks.

## Non-Goals

- Release automation that mutates git tags, GitHub releases, branch protection,
  or remote state. The `release` command validates a release record only.
- The boundary-split packaging action that assembles a delivery bundle by
  artifact disposition; it intersects the delivery-bundle guidance
  (Brad-Edwards/aces-scenario-packs#9) and is deferred.
- The authoring CLI and capture-workflow tooling, tracked separately
  (Brad-Edwards/aces-scenario-packs#13, Brad-Edwards/aces-scenario-packs#14).
- Validating or redefining ACES SDL semantics, which remain owned by ACES core.
