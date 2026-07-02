# Pack Manifest (Template)

This is a **template** pack manifest. It shows the *shape* of the minimum ACES
scenario pack defined in the [scenario-pack contract](../../contracts/scenario-pack-contract.md);
it is not a schema (the machine-readable schema is tracked in
Brad-Edwards/aces-scenario-packs#4). Replace every `PLACEHOLDER:` value with real
content before publishing, and delete guidance lines that do not apply.

## Identity

- Pack identifier: PLACEHOLDER: your-pack-id (stable, kebab-case, globally unique)
- Pack name: PLACEHOLDER: Human-readable pack name
- Pack version: PLACEHOLDER: 0.1.0 (SemVer, per ../../docs/versioning.md)

## ACES SDL Contract

- SDL contract version: PLACEHOLDER: aces-sdl-vX.Y (the ACES SDL contract this pack targets)

ACES core owns SDL semantics. A pack references and carries SDL by contract
version; it does not redefine SDL.

## Lifecycle

- Lifecycle state: Draft

Choose exactly one ACES-native maturity state: Draft, Candidate, Published,
Deprecated, or Withdrawn. A template pack starts in Draft.

## Provenance and Compatibility

- See [provenance.md](provenance.md) for the provenance and compatibility declaration.

## Scenarios

A pack MUST carry at least one scenario definition.

- [scenarios/example-scenario.md](scenarios/example-scenario.md)

## Optional Layers

Declare each optional layer explicitly. A directory alone never implies a
capability. Set each layer to `provided` or `not-provided`; when `provided`,
follow the layer's applicability and validation expectations in the contract.

- Oracle and Scoring: not-provided
- Proof: not-provided
- Challenge and Flag Adapter: not-provided
- Delivery and Audience Bundle: not-provided
