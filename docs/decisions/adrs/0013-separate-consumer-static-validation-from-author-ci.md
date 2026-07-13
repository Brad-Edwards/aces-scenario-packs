# ADR 0013 — Separate consumer static validation from author CI

- Status: Accepted
- Date: 2026-07-13
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0011](0011-require-pinned-aces-sdl-validation.md), and
  [ADR 0012](0012-pack-content-identity-and-trust-boundary.md)

## Context

`aces-pack-validate` validates all packs discovered in a catalog checkout. Its
author-CI role legitimately uses Git discovery and executes pack-local validators
and tests. A consumer ingesting one pack as foreign input needs only the static
pack contract and cannot safely invoke Git, subprocesses, or pack code.

Keeping a second consumer implementation beside the CLI would create two pack
contracts. Exposing the CLI's private helpers would instead make catalog globals,
console output, and author-only workflow behavior part of the library API. The
consumer boundary also has stricter diagnostic and filesystem requirements than
CI: input values and absolute paths must not reach a quasi-public error envelope,
and a contained-looking path must not escape through a symlink or a race.

File-backed ACES SDL parsing has one additional side effect to account for.
`parse_sdl_file()` can resolve imports; an allowlisted OCI import can perform
network I/O and populate `sdl/.aces/module-cache`. That is appropriate only when
the caller has deliberately admitted the resolver policy. It is not implied by a
"static, deterministic" request-time validation surface.

## Decision

The package exposes a public single-pack validation result and function from its
normal import surface. Invalid foreign input is represented by
`ValidationResult(ok, errors)` rather than by CLI exit state or a new exception
hierarchy. The function is silent: it does not log, print, mutate process globals,
read environment configuration, persist consumer state, invoke Git or a
subprocess, or execute pack-local code.

There is one shared static-validation authority. The catalog CLI delegates its
overlapping per-pack checks to that authority, then adds author-only discovery,
pack-local validators and tests, leak scanning, and other catalog workflow gates.
The public API never delegates to the CLI and consumers never import underscored
CLI helpers. Packaged schemas and the existing pack-domain JSON-Schema subset are
reused; no duplicate schemas or second schema loader are introduced. ACES SDL is
validated only through the pinned public ACES parser.

The consumer result covers exactly the static ingest contract:

- bounded, valid `pack.yaml` with the layout contract's identity fields;
- the required, referenced `docs/provenance-ledger.yaml`, its packaged schema,
  all-true content-safety attestations, required review gates, and matching pack
  name;
- a referenced compatibility manifest, when present, against the packaged
  compatibility schema; and
- every direct `sdl/*.sdl.yaml` document through ACES, with absence of a direct
  SDL document failing closed.

Author-CI-only checks do not silently migrate into this contract. Conversely,
the CLI must not retain a second copy of any check in the shared subset.

All consumer-controlled reads use the descriptor-anchored, no-follow pack
filesystem boundary established by ADR 0012, factored as shared internal
infrastructure rather than reached through `digest.py` private names. Paths are
canonical pack-relative paths; symlinks, hardlinks, special files, escaping
pointers, duplicate YAML mapping keys, invalid UTF-8, and unsupported descriptor
platforms fail closed. Input bytes, YAML expansion, SDL parser resources, member
and error counts, and individual diagnostic lengths are bounded. Validation is
deterministically ordered. Because a mutable directory cannot be snapshotted by
an API call, consumers still acquire and immutably stage a pack before validation
and promote those same bytes afterward.

Errors contain only stable error classes/codes, bounded field paths, and bounded
pack-relative filenames. They never include input values, YAML or SDL bodies,
absolute paths, raw exception messages, credentials, participant/operator tokens,
or ACES diagnostic prose. Expected malformed-input and filesystem failures join
the result; unexpected programming defects are not swallowed and mislabeled as
pack invalidity.

SDL import resolution is denied by default for this consumer surface. ACES 0.20
does not expose a resolver-policy seam for file-backed parsing, and distinguishing
local from remote imports would require a second pre-parser. Until the exactly
pinned ACES version provides such a seam, consumer validation uses ACES content
parsing and therefore fails closed for every document containing imports. It
must not monkeypatch ACES, pre-parse SDL with a second semantic parser, or
silently perform network I/O. The validation API owns no cache or other
persistence.

A keyword-only resource-limit policy is the extension seam for consumers that
need stricter request budgets. The simple `validate_pack(pack_root)` call keeps
safe defaults. New contract checks are added to the shared static authority only
when they are genuinely ingest-time checks; author workflow checks remain CLI
composition rather than boolean options on the library API.

## Consequences

- The package remains the one version-matched authority for pack layout,
  pack-owned schemas, and ACES-backed SDL validation across authors and
  consumers.
- ADR 0011's "single catalog-validation entry point" remains true for catalog
  author CI, but no longer excludes a public single-pack consumer API.
- The stronger foreign-input boundary may reject filesystem shapes tolerated by
  the historical CLI. That is intentional; catalogs should correct unsafe pack
  shapes rather than preserve them as compatibility behavior.
- Resolver side effects are explicit. A request-time caller can rely on the
  default API not reaching the network or writing an ACES cache; an author CI
  caller may continue to use ACES resolution under its separately controlled
  environment.

## Non-goals

This decision does not add catalog discovery, Git integration, pack-local
validators or tests, leak scanning, flag-placement joins, release readiness,
content-manifest/digest verification, acquisition, archive extraction,
authentication, authorization, storage, promotion, or registry behavior. It
does not define or extend SDL, trust, scoring, telemetry, oracle, or other
ACES semantics.
