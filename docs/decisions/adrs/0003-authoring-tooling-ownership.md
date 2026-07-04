# ADR 0003: Authoring And Tooling Ownership

Date: 2026-07-04

Status: Accepted

## Context

ASP-0013 requires the repository to decide which scenario-pack authoring helpers
move into this companion repository and which remain in ACES core or downstream
consumers, before any helper is moved, duplicated, or coupled across
repositories. [ADR 0002](0002-scenario-pack-validation-tooling.md) and
`tools/README.md` both deferred this ownership plan to
Brad-Edwards/aces-scenario-packs#13. Validation and release checks are already
owned here; the authoring CLI, capture workflows, and state-mutating release
automation were left unassigned.

## Decision

Record authoring-helper ownership by category and inventory, and require that
record to exist before any helper moves. The full inventory, category
vocabulary, and follow-up links live in the
[authoring and tooling ownership plan](../../authoring-tooling-ownership.md);
this ADR captures the durable decision:

- This repository owns **pack-structure authoring helpers** and **validation
  helpers** that operate on an untrusted pack root without secrets, network
  access, private repository state, or downstream catalog vocabulary. Future
  authoring helpers (a pack scaffolding CLI, metadata/provenance generators)
  adopt here and reuse the `aces_pack_tools` contract instead of forking a
  parallel one.
- ACES core keeps **SDL-semantic helpers**; the authoring/capture tooling
  boundary and CI/reference integration are tracked by `aces#629` and `aces#630`.
- **Downstream runtime / capture helpers** stay downstream; capture workflow
  placement is deferred to Brad-Edwards/aces-scenario-packs#14 and `aptl#591`.
- **State-mutating release automation and boundary-split packaging** are
  deferred to the delivery-bundle guidance, Brad-Edwards/aces-scenario-packs#9.
- No helper moves before its ownership row is recorded in the plan.

## Consequences

- The authoring CLI has a recorded home before any code is written or moved, so
  the next tooling issue can build in this repository against a decided boundary.
- Helpers not owned here remain visibly tracked by their ACES-side or downstream
  follow-up issue rather than drifting into this repository by default.
- The category vocabulary lets future helpers be placed without re-opening the
  decision, and a structural test keeps the inventory honest (every helper row
  carries a source path, owner, proposed owner, and migration decision).

## Non-Goals

- Move any helper, including ACES core SDL validators or downstream capture
  assets, in this change.
- Open new ACES-side or downstream follow-up issues; the existing tracked issues
  are linked, not created.
- Build the pack scaffolding CLI or metadata generators; this ADR only assigns
  their owner.
