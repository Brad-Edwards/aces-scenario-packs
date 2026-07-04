# Tools

This directory houses the reusable, stdlib-only tooling for ACES scenario packs.
Validation and release tooling must follow the
[tooling design guardrails](../docs/tooling-design-guardrails.md) so it reuses
the existing contract, schema index, scrub, profile, release, and CI boundaries
instead of creating a parallel contract surface. Tooling that depends on ACES
core or APTL must document that boundary explicitly before it is moved here.

## `aces_pack_tools`

`aces_pack_tools/` is a self-contained, stdlib-only Python package
(no third-party dependencies) that runs static, offline checks against a pack.
It requires no credentials, no network access, and no private repository state,
and it treats a pack root as untrusted input. It is decided in
[ADR 0002](../docs/decisions/adrs/0002-scenario-pack-validation-tooling.md).

### Commands

Run it as a module with the `tools/` directory on `PYTHONPATH`:

```sh
PYTHONPATH=tools python3 -m aces_pack_tools <command> ...
```

- `validate <target> --schema-index schemas/index.json` — validate pack records
  against the published schemas. With `--family <family>` the target is a single
  JSON record; with a directory target the tool validates each `<family>.json`
  record it finds (its discovery convention), checks `packId` consistency, runs
  the runtime-profile portability gate, checks artifact-boundary paths stay
  within the pack, and — when a `runtime-visibility.json` record is present —
  runs the runtime-visibility containment, tier-conflict, and participant
  leak-scan gates.
- `leak <target> [--denylist terms.txt]` — scan a file or directory for
  secret-shaped material (private keys, cloud access keys, bearer tokens,
  assigned secrets) and any caller-supplied denylisted vocabulary term. The
  denylist is configuration; the tool ships none, so it carries no
  downstream-private vocabulary itself.
- `visibility <pack-dir> [--denylist terms.txt]` — check a pack's
  `runtime-visibility.json` record: schema conformance, per-root path
  containment, tier-conflict detection, and a leak scan of every
  participant-visible root for secret-shaped and operator/oracle material. This
  is the release/CI entry point that re-runs the participant scan with a
  caller-supplied operator/oracle denylist. A pack with no visibility record is
  clean.
- `release <record> --schema-index schemas/index.json` — validate a release
  record and cross-check its `schemaVersions` against the schema index.

Add `--format json` for machine-readable output. Exit codes: `0` clean, `1`
findings, `2` usage or IO error. Findings report the check, a pack-relative path,
the schema family or gate, and a concise reason — never file contents or secrets.

### Consumer CI

A runnable, secret-free GitHub Actions example lives in
[`../examples/ci/`](../examples/ci/README.md) for external adopters to copy.

## Ownership and boundaries

`aces-scenario-packs` owns this static pack validation and release-check tooling.
Deliberately **not** owned here yet, tracked separately:

- Release automation that mutates git tags, GitHub releases, or remote state, and
  the boundary-split packaging action that assembles delivery bundles — deferred
  (packaging intersects the delivery-bundle guidance,
  Brad-Edwards/aces-scenario-packs#9).
- The authoring CLI and its ownership plan are recorded in the
  [authoring and tooling ownership plan](../docs/authoring-tooling-ownership.md)
  (ADR 0003, Brad-Edwards/aces-scenario-packs#13): pack-scaffolding and
  metadata-authoring helpers are owned here and adopt this same tooling contract,
  but are not built yet.
- Capture and inventory workflow placement — Brad-Edwards/aces-scenario-packs#14.
