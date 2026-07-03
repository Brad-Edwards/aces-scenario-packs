# Schemas

This directory holds the published, machine-readable scenario-pack schemas. They
implement the [ACES scenario-pack contract](../contracts/scenario-pack-contract.md)
and follow the [schema design guardrails](../docs/schema-design-guardrails.md).
The schemas do not redefine ACES SDL semantics.

## Schema index

[`index.json`](index.json) is the **source of truth** for published schemas. Each
entry records the schema's `family`, `id`, `path`, `version`, `status`,
`source`/`ownership` notes, `compatibility_impact`, and `fixtures`. Add, change,
or retire a published schema only through this index; the test suite fails on any
schema file that is not indexed and on any index entry missing its notes.

## Schema families

All families are JSON Schema Draft 2020-12 and version-lined with a
`urn:aces-scenario-pack:schema:<family>:v0` identifier.

- **pack-metadata** — pack identity, version, targeted ACES SDL contract version,
  scenario references, lifecycle state, and declared optional layers.
- **compatibility** — the pack's declared ACES and pack-version compatibility and
  its compatibility boundary.
- **provenance** — source, ownership, scrub status, and adoption impact
  (references only).
- **artifact-boundary** — which artifacts are authored, generated, included,
  excluded, or consumer-supplied.
- **runtime-profile** — portable, ACES-native runtime expectations.
- **delivery-bundle** — audience and packaging in portable terms.
- **lifecycle** — pack maturity state from the contract's ACES-native set.
- **validation** — validation evidence for a pack.
- **release** — release version, published schema versions, compatibility impact,
  and migration notes.

## Compatibility impact

Published artifacts (the contract and its schemas) use Semantic Versioning per
[versioning.md](../docs/versioning.md). Every schema records its own version and
its compatibility impact in the index. The current set is pre-1.0 (`0.y.z`) with
no prior published version, so each schema's impact is additive; pre-1.0 releases
make no backward-compatibility promise. A change that alters a published schema
must update this index and ship a loadable validation fixture, per
[`.gc/plan-rules.md`](../.gc/plan-rules.md).

## Validation coverage

Every schema ships at least one loadable fixture under [`examples/`](examples/).
`tests/test_pack_schema_index.py` proves each schema is loadable and well-formed,
that the index and on-disk schema set agree, and that each fixture conforms to its
schema, using the shared conformance checker in `tools/aces_pack_tools`. Reusable,
offline pack validation and release-check tooling for external adopters lives in
[`../tools/`](../tools/README.md) (Brad-Edwards/aces-scenario-packs#5); full
release automation remains deferred.
