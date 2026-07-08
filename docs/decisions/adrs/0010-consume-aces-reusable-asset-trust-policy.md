# ADR 0010 — Consume ACES reusable-asset trust policy for pack provenance

- Status: Accepted
- Date: 2026-07-08
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md)

## Context

[ADR 0009](0009-scenario-packs-subordinate-to-aces.md) makes ACES conformance
the dominating objective and forbids this repository from defining ACES
semantics. ACES core owns the reusable-asset trust policy at
`contracts/schemas/asset-trust/reusable-asset-trust-policy-v1.json`
(`$id: https://aces.dev/schemas/reusable-asset-trust-policy-v1.json`,
`schema_version: reusable-asset-trust-policy/v1`). That policy covers scenario
packs as reusable ACES assets: its `asset_family` vocabulary includes
`reusable_scenario` and `sdl_module`, and its evidence classes include
`integrity_digest`, `authenticity_signature`, `provenance_lock_record`,
`governance_source`, and `artifact_checksum` with enforcement levels.

The local `provenance.schema.yaml` currently carries a pack-side provenance and
publication ledger. Some of that ledger is genuinely pack-domain content
management: licensing, redistribution classification, content-safety exclusion
attestations, review gates, and customer-overlay containment. Other parts risk
becoming a parallel trust model if they are used to assert integrity,
authenticity, provenance lock, governance source, or checksum semantics already
owned by ACES.

ACES schemas are currently `stability: draft`, so hard-pinning a copied schema in
this package would create a second source of truth exactly where ACES is still
settling the upstream contract.

## Decision

The ACES reusable-asset trust policy is the authority for scenario-pack
integrity, authenticity, provenance-lock, governance-source, artifact-checksum,
asset-family, and enforcement semantics.

This repository consumes that policy from the published `aces-sdl` contract
corpus, through the upstream contract APIs such as `aces_contracts.corpus` and
`schema_bundle()`. It does not vendor the policy, restate its schema, fork its
enums, or define local substitutes for its evidence classes.

The local provenance ledger remains a pack-domain ledger only for facts absent
from the ACES trust policy:

- source-origin, licensing, attribution, and redistribution facts needed to
  decide what a catalog may publish, sell, or hand to a customer;
- content-safety exclusion attestations, including no real malware, no real
  third-party targets, no real credentials, no sensitive data, and safe
  offensive-tooling boundaries;
- publication-review gates for licensing, attribution, sensitive data,
  offensive tooling, and customer-overlay handling;
- customer-overlay roots and distribution classifications needed to keep private
  customer content path-contained and removable from the base pack.

Every retained provenance field must have one documented status:

- mapped to an ACES trust-policy concept, using ACES names and enforcement
  semantics; or
- retained as pack-domain metadata that ACES does not define.

Pack assets map to `asset_family: reusable_scenario`. SDL units are treated as
`asset_family: sdl_module` only when the implementation is explicitly validating
or describing an SDL module as its own reusable ACES asset. Distribution classes
such as `open`, `redistributable`, `commercial-only`, and `customer-specific`
remain pack-domain publishing classes; they are not ACES trust evidence classes
and must not be used as replacements for ACES enforcement levels.

While the upstream policy is draft, this package references and validates
against the published ACES corpus version it depends on, but does not freeze a
copied policy into `src/aces_scenario_packs/resources/schemas/`. Once ACES marks
the policy stable, this repository may pin an explicit supported upstream
contract version through package dependency metadata and compatibility tests.

## Consequences

- The implementation must update the provenance schema, contract prose, template
  example, validation tests, and release metadata tests together when the ledger
  shape changes. A schema-only change is not sufficient because
  `aces-pack-validate` applies additional cross-field gates.
- `content_ci.py` remains the repo-wide validation entry point. New ACES
  trust-policy checks must live behind that gate and reuse its existing
  path-containment, duplicate-id, source-reference, overlay-containment, and
  redacted-error patterns.
- `release.py` must keep provenance output bounded to counts, classes, statuses,
  and ACES trust-policy identifiers. Release manifests and logs must not include
  raw source prose, review prose, customer-specific detail, secrets, credentials,
  or operator/oracle vocabulary.
- The local JSON-schema subset validator is acceptable for local pack-domain
  schemas, but it is not the authority for ACES schemas. If full ACES schema
  validation is needed, it must be reached through the ACES contract corpus or a
  narrow adapter in the existing validation gate, not by copying ACES schemas or
  creating a second schema-loading system.
- If a pack needs trust expressivity not present in the ACES reusable-asset
  policy, the gap is raised upstream in ACES. This repository does not add a
  local extension point for it.
