# ADR 0012 — Pack content identity consumes ACES associated-artifact manifests

- Status: Accepted
- Date: 2026-07-12
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0010](0010-consume-aces-reusable-asset-trust-policy.md), and
  [ADR 0011](0011-require-pinned-aces-sdl-validation.md)
- Upstream decision: ACES ADR-077, `associated-artifact-manifest-v1`

## Context

A consumer can validate pack files and retain a caller-supplied digest without
proving that the digest identifies the validated bytes. The first design for
issue 95 attempted to close that gap with a pack-owned digest over every file in
a directory. That would have created a second asset identity and checksum model
beside ACES and would have treated a live-directory traversal as the portable
asset model.

ACES ADR-077 now owns the missing abstraction. One closed
`associated-artifact-manifest-v1` attaches an exact keyed set of non-semantic
artifact descriptors to a scenario, sealed scenario snapshot, or experiment
parent. ACES owns the descriptor/checksum/reference shapes,
`associated-artifact-set/v1` canonicalization, the derived set digest, structured
diagnostics, and full parent/set/payload byte-binding validator. The associated
set is a distinct reusable-asset family; it does not change SDL semantic
identity or prove authenticity.

This repository still must select and safely materialize the bytes that comprise
a scenario pack. That is a packaging responsibility, not authority to define a
second canonical digest.

## Decision

Scenario-pack content identity is the **validator-derived ACES associated-artifact
set digest**. This repository consumes ACES's public model and validator and
defines only the following pack-owned projection:

1. A pack that opts into content identity declares
   `associated_artifact_manifest` in `pack.yaml`. The target is a contained,
   pack-relative JSON file parsed through ACES's duplicate-member-rejecting
   loader. The manifest carrier is not one of its own payloads.
2. The manifest has `scope: scenario`; its parent id equals `pack.yaml.name`, its
   logical id is `<pack-name>-associated-artifacts`, and its manifest version
   equals the pack version. ACES remains responsible for matching the concrete
   parsed scenario or scenario snapshot.
3. Artifact locators use the pack-owned absolute URI form
   `aces-scenario-pack:/<percent-encoded-root-relative-path>`. Artifact ids remain
   opaque ACES manifest-local ids; the URI is only a locator. This package
   resolves it beneath the opened pack root and supplies concrete byte readers
   to ACES. No network or ambient URI resolution occurs.
4. The manifest must cover the exact regular-file inventory. The carrier and the
   exact `sdl/.aces/module-cache/` resolver cache are excluded; every other file
   is referenced at least once and every referenced pack URI resolves to an
   inventoried file. Unknown files therefore fail instead of escaping identity.
5. Scenario-pack payload descriptors use SHA-256. ACES derives the set digest
   over the parent plus descriptors and independently verifies every declared
   checksum and size from the supplied readers.

The public library separates authoring derivation from consumer verification:

- `derive_pack_content_manifest()` recomputes payload checksums, sizes, and the
  ACES set digest from an immutably staged pack while preserving the authored
  descriptor metadata. Authoring/release tooling persists the returned model.
- `validate_pack_content_manifest()` requires the declared model, concrete SDL
  parent, exact inventory, set digest, sizes, checksums, and bytes to agree.
- `pack_content_digest()` returns the validated model's set digest.
- `verify_pack_content_digest()` derives no trust from its caller-supplied value;
  it fully validates the pack first and then compares the expected and actual
  canonical digests.

Filesystem traversal and reads are anchored to opened directory descriptors and
use no-follow opens. Symlinks, special files, hardlinks, non-canonical names or
URIs, escaping paths, missing/extra members, unreadable data, and an inventory
change during the operation fail closed with bounded errors. ACES diagnostics
remain structured on the pack-domain error rather than being replaced by local
checksum semantics.

No directory operation can make mutable storage atomic. Callers must acquire and
immutably stage the pack, validate it and its content manifest, atomically
promote the same verified bytes, and reverify before use when storage guarantees
do not make that redundant. Modes, ownership, ACLs, and extended attributes are
outside the associated-artifact set and must be materialized with safe fixed
policy.

This adds a portable manifest/pointer and advances the scenario-pack contract
content version to `2`. The package dependency remains exactly pinned while
ACES contracts are draft. This change cannot merge or publish until an ACES
release contains ADR-077's model, schema corpus, and validator; local development
may use the merged upstream `dev` worktree, but the final gate installs the
published wheel.

## Consequences

- Pack content and metadata have one ACES-defined identity without vendoring an
  ACES schema or inventing a second canonicalization profile.
- Raw SDL files may be associated payloads, but associated bytes do not alter the
  validated scenario's semantic digest. Parent integrity, set integrity,
  per-payload checksums, and authenticity remain separate claims.
- A stale or caller-asserted package digest, shape-only manifest validation, or
  URI/path assertion cannot establish conformance. Every payload must be bound to
  concrete staged bytes.
- Separate release/export views require separate manifests because attachment
  and set identity do not inherit across parents or materialized byte sets.
- Public pack validation (#94) should reuse the descriptor-anchored filesystem
  boundary introduced here rather than reintroduce path-based safety checks.

## Non-goals

This decision does not define SDL semantics, ACES trust admission, signatures,
archive or OCI formats, acquisition, storage, entitlement, launchability,
catalog persistence, or a registry. It does not fetch artifact URIs, execute
pack code, invoke subprocesses, or claim snapshot isolation over a mutable
directory.
