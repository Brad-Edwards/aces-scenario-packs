# ACES Scenario-Pack Contract

Status: Normative (v0, pre-1.0)

This document is the public contract for an ACES scenario pack. It defines the
minimum pack shape, the rules for optional pack layers, the ACES-native
terminology the ecosystem uses, the lifecycle states a pack moves through, and
the compatibility boundaries between ACES core, this repository, and downstream
consumers.

It is normative for pack authors and for the schemas, templates, tooling, and
examples this repository will publish. It is pre-1.0: the surface may change
without a compatibility guarantee until the first release, per
[versioning.md](../docs/versioning.md). The contract boundary is fixed by
[ADR 0001](../docs/decisions/adrs/0001-scenario-pack-contract-boundary.md).

## Terminology

These terms are ACES-native and independent of any downstream catalog,
platform, or product.

- **Scenario pack** — a self-contained, reusable unit that packages one or more
  ACES scenario definitions together with the metadata, provenance, and
  compatibility declarations needed to adopt them. A pack is the primary
  distribution artifact of this repository.
- **Pack manifest** — the declarative metadata at the root of a pack that
  identifies it, declares the ACES SDL contract version it targets, and lists
  the scenarios and optional layers it provides.
- **Scenario definition** — a unit of scenario content expressed in the ACES
  Scenario Definition Language (SDL). Its semantics are owned by ACES core; a
  pack references and carries SDL, it does not redefine it.
- **Pack layer** — an optional, self-describing capability a pack MAY provide in
  addition to its base scenarios (for example, scoring or proof material). Each
  layer declares its own applicability and validation expectations.
- **Compatibility boundary** — the declared line between what a pack owns and
  what ACES core or a downstream consumer owns, used to reason about breaking
  change.
- **Lifecycle state** — the maturity or publication state of a pack as an
  authored artifact. It describes the pack, not any downstream consumer's
  workflow state.

## Minimum Pack Shape

Every ACES scenario pack MUST provide the following elements. This section
describes the required *shape*; the machine-readable schema for each element is
deferred to the pack-metadata schema work (Brad-Edwards/aces-scenario-packs#4).

- **Identity and metadata** — a pack manifest carrying a stable pack identifier,
  a human-readable name, and a version using the scheme in
  [versioning.md](../docs/versioning.md).
- **SDL contract reference** — an explicit declaration of the ACES SDL contract
  version the pack targets, so consumers can reason about compatibility.
- **At least one scenario definition** — a pack MUST carry one or more ACES SDL
  scenario definitions; a pack with no scenarios is not a scenario pack.
- **Provenance and compatibility declaration** — a record of where the pack's
  content originated and the compatibility boundary it claims (see
  [Compatibility Boundaries](#compatibility-boundaries)).
- **Lifecycle state** — the pack MUST declare its current lifecycle state from
  the canonical set below.

A pack MAY provide any of the optional layers below. Optional layers are never
part of the minimum shape and their absence MUST NOT make a pack invalid.

## Optional Layers

Optional layers are explicit pack capabilities. Each layer a pack provides MUST
be declared in the manifest and MUST satisfy its own applicability and
validation expectations. A layer is never implied by folder convention; it is
declared, so that tooling can test for its presence and correctness. The
detailed schema and tooling for each layer are deferred to the follow-up issues
referenced below.

### Layer: Oracle and Scoring

- Applicability: packs that define how a scenario outcome is judged or scored.
- Validation: the layer MUST declare, in ACES-native terms, what it evaluates
  and how a result is produced, and MUST be resolvable without any downstream
  scoreboard or product runtime. Detailed model deferred to
  Brad-Edwards/aces-scenario-packs#6.

### Layer: Proof

- Applicability: packs that ship golden or live-reference proof material for
  their scenarios.
- Validation: the layer MUST identify each proof artifact and state whether it
  is golden (static reference) or live-reference, in ACES-native language, with
  no dependency on private infrastructure. Guidance deferred to
  Brad-Edwards/aces-scenario-packs#7.

### Layer: Challenge and Flag Adapter

- Applicability: packs that expose scenarios as challenges with flags or
  equivalent completion tokens.
- Validation: the layer MUST describe the adapter contract in ACES-native terms
  and MUST NOT embed a downstream catalog's flag format, status vocabulary, or
  platform assumptions. Guidance deferred to
  Brad-Edwards/aces-scenario-packs#8.

### Layer: Delivery and Audience Bundle

- Applicability: packs that describe how their scenarios are bundled for a
  particular audience or delivery mode.
- Validation: the layer MUST declare the bundle's audience and packaging in
  ACES-native terms and MUST remain adoptable independent of any specific
  downstream delivery system. Guidance deferred to
  Brad-Edwards/aces-scenario-packs#9.

## Lifecycle States

A pack's lifecycle state describes its maturity and publication status as an
authored artifact. These states are ACES-native and describe the pack only.
They deliberately do NOT reuse downstream catalog or challenge-platform workflow
statuses (such as a per-consumer "assigned", "in-play", "solved", or "retired"
status); those belong to the consumer, not to the pack contract.

Canonical states: Draft, Candidate, Published, Deprecated, Withdrawn.

- **Draft** — under active authoring; not yet offered for adoption.
- **Candidate** — feature-complete and offered for review; may still change
  before publication.
- **Published** — released for adoption under the versioning policy; changes
  follow the compatibility rules in [versioning.md](../docs/versioning.md).
- **Deprecated** — still published but superseded; consumers should migrate.
- **Withdrawn** — no longer offered for adoption; retained only for provenance.

A pack declares exactly one lifecycle state at a time in its manifest.

## Compatibility Boundaries

The scenario-pack contract sits between ACES core and downstream consumers. The
boundary below mirrors the [repository charter](../docs/repository-charter.md)
and the [authoring boundary](../docs/authoring-boundary.md); the three are kept
aligned on purpose.

- **ACES core** owns the Scenario Definition Language and its runtime-independent
  semantics. A pack references and carries SDL by contract version; it never
  redefines SDL semantics.
- **This repository** owns pack structure, optional-layer rules, terminology,
  lifecycle vocabulary, and the schemas, templates, tooling, and validation that
  make a pack authorable and adoptable.
- **Downstream consumers** consume the pack contract and MAY add private
  runtime, delivery, class-management, or product integrations outside the
  canonical pack contract. Those integrations MUST NOT be assumed by, or encoded
  into, the pack contract.
- **Capture and inventory workflows** are intentionally out of this contract
  until their ownership is resolved (Brad-Edwards/aces-scenario-packs#14); a
  pack MUST NOT assume any particular placement of those workflows.

Compatibility is reasoned about through the pack's declared SDL contract version
and its own pack version. Breaking changes follow the semantics in
[versioning.md](../docs/versioning.md).

## Open Questions

Open questions are tracked as follow-up issues rather than resolved inline, so
this base contract can stabilize while dependent surfaces are designed
separately.

- Pack metadata, compatibility, and lifecycle schemas —
  Brad-Edwards/aces-scenario-packs#4.
- Validation and release tooling that enforces this contract —
  Brad-Edwards/aces-scenario-packs#5.
- Oracle and scoring model detail for the scoring layer —
  Brad-Edwards/aces-scenario-packs#6.
- Golden and live-reference proof guidance for the proof layer —
  Brad-Edwards/aces-scenario-packs#7.
- Flag and challenge-adapter guidance for the challenge layer —
  Brad-Edwards/aces-scenario-packs#8.
- Delivery and audience bundle guidance for the delivery layer —
  Brad-Edwards/aces-scenario-packs#9.
- A safe ACES-native example pack that exercises this shape —
  Brad-Edwards/aces-scenario-packs#10.
- Capture and inventory workflow placement relative to pack authoring —
  Brad-Edwards/aces-scenario-packs#14.
