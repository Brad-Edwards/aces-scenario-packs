# ADR 0016 — Manifest-led catalog pack discovery

- Status: Accepted
- Date: 2026-07-15
- Extends: [ADR 0002](0002-distribute-as-installable-package.md),
  [ADR 0009](0009-scenario-packs-subordinate-to-aces.md), and
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md)

## Context

Catalog author CI historically treated Git-visible directories directly below
`scenarios/` as packs, even when they had no `pack.yaml`. That makes shared prose,
design material, caches, and other catalog-owned directories enter pack checks
and potentially exposes their pack-shaped Python files to author-workflow
execution. A hard-coded drift scan also coupled the reusable package to one
downstream pack, path, and issue sequence.

Git visibility is not pack identity. A reserved-name or per-catalog skip list
would move downstream layout policy into the reusable package and would require
every new non-pack directory to update configuration. Parsing `pack.yaml` during
discovery would instead create a second manifest validator beside the shared
static authority established by ADR 0013. Release `check --all` must not acquire
a separate interpretation of the catalog.

## Decision

Catalog discovery is manifest-led. A candidate pack is exactly a real, direct
child directory of `<catalog-root>/scenarios/` that contains a direct directory
entry named `pack.yaml`. Discovery is shallow, does not follow a directory
symlink, does not recurse, query Git, parse YAML, inspect manifest fields, execute
pack code, or apply reserved-name, issue-history, or catalog-policy filters.
Candidate names are sorted deterministically.

The marker establishes candidacy, not validity. The shared static-validation
authority in `validation.py`, reached by author CI through
`_validate_pack_for_author_ci()`, decides whether the marker is a safe regular
file and whether its bytes, shape, identity, pointers, schemas, and ACES SDL are
valid. A symlink, special file, malformed YAML document, duplicate key, missing
identity, or directory-name mismatch is therefore a validation failure, not a
discovery rule. No second parser, schema, or exception hierarchy is introduced.

Author-only pack-local validators and tests may execute only after that
candidate's shared static validation succeeds. Candidate selection alone is not
authorization to execute code. Static validation retains its descriptor-
anchored, no-follow filesystem reads, resource limits, deterministic bounded
diagnostics, and separation between expected input failures and package defects.

Author CI owns one internal discovery authority parameterized by the scenarios
root. Each command takes one immutable, sorted snapshot and passes that snapshot
through its catalog checks; checks do not rediscover independently. The catalog
root remains the runtime parameter established by ADR 0002, with the current
working directory as the CLI default. `aces-pack-release check --all` consumes
the same authority and snapshot contract rather than walking `scenarios/`
itself. Explicit single-pack selection is not catalog discovery and retains its
existing containment and validation obligations. The public `validate_pack()`
API remains single-pack and gains no catalog or Git behavior.

Discovery and validation failures use the existing CLI failure aggregation and
exit status. Diagnostics contain only bounded catalog-relative locations and
stable classes; they do not emit manifest bodies, raw exception text, absolute
paths, secrets, credentials, or participant/operator tokens. An absent
`scenarios/` directory is an empty catalog; an unreadable or unstable directory
fails closed rather than being reported as empty.

The downstream-specific drift scan is removed, not generalized. Catalog-local
paths, pack names, issue history, migration rules, and policy checks belong in
the downstream catalog. The reusable package carries only portable pack-layout
and authoring/validation/release rules.

## Consequences

- A directory without a direct `pack.yaml` is intentionally invisible to pack
  gates. Adding the marker is the explicit act that admits it as a candidate;
  missing markers are not inferred from other files or Git state.
- There is no reserved-directory configuration seam. A scaffold stored below
  `scenarios/` must omit the marker or live elsewhere; a marker-bearing
  `_template` is a candidate like any other directory.
- Packs created after a command takes its snapshot wait until the next run.
  Pack-local code cannot change which packs the current run checks.
- The reusable extension seam is the explicit catalog/scenarios root, not a
  downstream skip list or policy callback. Future catalog-root binding changes
  do not alter pack identity.
- Release and author CI cannot drift on discovery ordering, depth, marker name,
  Git state, or reserved directories because they share one authority.

## Non-goals

This decision does not define or extend ACES semantics, add a pack registry or
catalog schema, validate nested catalogs, infer incomplete packs, configure
reserved names, or host catalog policy. It does not make author CI a safe
sandbox for arbitrary pack-local code, change the public single-pack validation
API, add authentication or authorization, read secrets or environment
credentials, perform network access, persist discovery state, or change release
artifact construction.
