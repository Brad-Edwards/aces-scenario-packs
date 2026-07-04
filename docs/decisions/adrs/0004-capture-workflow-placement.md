# ADR 0004: Capture Workflow Placement

Date: 2026-07-04

Status: Accepted

## Context

ASP-0014 requires the repository to decide whether capture and inventory
workflows move into this companion repository, remain in ACES core, move to
APTL, or split by responsibility, before any capture asset is moved, duplicated,
or coupled across repositories. [ADR 0003](0003-authoring-tooling-ownership.md)
and the [authoring and tooling ownership plan](../../authoring-tooling-ownership.md)
recorded the capture row as *Deferred — capture placement review* and pointed it
at Brad-Edwards/aces-scenario-packs#14 and `aptl#591`. Capture work mixes three
different responsibilities — SDL-semantic meaning, portable pack-authoring
support, and runtime execution — that do not all belong in one repository.

## Decision

Split capture and inventory work **by responsibility, not by source
repository**. The full category vocabulary, responsibility inventory, and
follow-up links live in the
[capture workflow placement decision](../../capture-workflow-placement.md); this
ADR captures the durable decision:

- **ACES-semantic capture responsibility stays in ACES core.** Capture meaning
  that is SDL participant/evidence or runtime-independent scenario semantics
  remains normative in ACES core; this repository references it through the
  published scenario-pack contract instead of redefining it. Tracked by
  `aces#629`.
- **Pack-authoring capture support is owned by this repository on adoption, not
  by default.** A portable, offline capture-support asset may be adopted here
  only through a future linked issue, and must reuse the `aces_pack_tools`
  contract and resolve schemas through `schemas/index.json`. No such asset is
  adopted in this change.
- **APTL/runtime capture responsibility stays downstream.** Concrete inventory
  collection, range orchestration, attack-path execution, and runtime adapters
  remain with APTL or the consuming runtime. Tracked by `aptl#589` and
  `aptl#591`.
- No capture or inventory asset moves before this decision and its linked
  follow-up record a placement for that asset.

## Consequences

- The capture placement question deferred by ADR 0003 is now resolved, so the
  ownership plan's capture row records a decision rather than a deferral.
- Capture work has a responsibility-category seam, so future capture assets can
  be placed without re-opening this decision.
- Capture responsibilities not owned here remain visibly tracked by their
  ACES-side or downstream follow-up issue rather than drifting into this
  repository by default.
- A structural test keeps the decision honest: the decision doc must classify
  all three responsibility categories, inventory each by owner and placement,
  link the ACES and APTL follow-ups, and carry the no-move guardrail.

## Non-Goals

- Move, duplicate, or couple any capture or inventory asset, in either direction,
  in this change.
- Open new ACES-side or downstream follow-up issues; the existing tracked issues
  (`aces#629`, `aptl#589`, `aptl#591`) are linked, not created.
- Adopt any pack-authoring capture-support helper; this ADR only decides where
  such work would be owned.
- Redefine ACES SDL capture semantics or encode downstream catalog capture
  vocabulary into canonical pack terminology.
