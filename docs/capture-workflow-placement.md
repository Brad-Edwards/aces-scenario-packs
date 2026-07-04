# Capture Workflow Placement Decision

This decision records whether capture and inventory workflows move into this
companion repository, remain in ACES core, move to APTL, or split by
responsibility. It satisfies ASP-0014 and resolves the capture placement review
that [ADR 0003](decisions/adrs/0003-authoring-tooling-ownership.md) and the
[authoring and tooling ownership plan](authoring-tooling-ownership.md) deferred
to Brad-Edwards/aces-scenario-packs#14 and `aptl#591`. The decision is recorded
at decision altitude in
[ADR 0004](decisions/adrs/0004-capture-workflow-placement.md) and applies the
[authoring and capture boundary](authoring-boundary.md) ("Capture Placement
Review Guardrails"), [ADR 0001](decisions/adrs/0001-scenario-pack-contract-boundary.md),
and the [tooling design guardrails](tooling-design-guardrails.md).

## Purpose

Capture workflow ownership affects ACES SDL semantics, reusable pack authoring,
and downstream runtime responsibilities, so it must be decided **before** any
capture or inventory asset is moved, duplicated, or coupled across repositories.
This decision classifies capture work by the responsibility it actually
performs, records the owner and placement for each, and links the ACES-side and
APTL follow-ups that track anything not owned here. No capture asset is moved by
this change.

## Capture Responsibility Categories

Capture and inventory work is classified by the responsibility it performs, not
by the repository that happens to hold it today. The category, not the current
file path, drives the placement default. The three categories match the
acceptance criteria for ASP-0014 and the preflight guardrails recorded in the
[authoring and capture boundary](authoring-boundary.md).

- **ACES-semantic capture responsibility** — definitions or checks that change
  SDL participant, evidence, or runtime-independent scenario semantics: what a
  captured artifact *means* in the Scenario Definition Language. Default owner:
  ACES core, unless the asset only references public pack structure.
- **Pack-authoring capture support** — portable, offline pack guidance,
  metadata, provenance, artifact-boundary declarations, runtime-profile
  declarations, and static validation that help authors *describe* capture
  expectations inside a pack without executing capture. Default owner: this
  repository, when the asset reuses the published scenario-pack contract and
  `schemas/index.json` and can operate on an untrusted pack root without
  secrets, network access, private repository state, or downstream catalog
  vocabulary.
- **APTL/runtime capture responsibility** — concrete inventory collection,
  range orchestration, attack-path execution, runtime adapters, environment
  binding, credentials, private repository state, or product-specific workflow
  behavior. Default owner: downstream (APTL or a consumer), unless a linked
  ownership issue explicitly extracts a portable pack-authoring subset.

## Capture Placement Decision

**Split capture and inventory work by responsibility, not by source
repository.** When a single workflow mixes SDL-semantic meaning, pack metadata,
and runtime execution, it is split along the responsibility categories above
rather than moved wholesale between repositories.

- **ACES-semantic capture responsibility stays in ACES core.** Capture meaning
  that is SDL semantics remains normative in ACES core; this repository
  references it through the published contract rather than redefining it.
- **Pack-authoring capture support is owned by this repository — on adoption,
  not by default.** A portable, offline capture-support asset may be adopted
  here when it reuses the `aces_pack_tools` contract and resolves schemas
  through `schemas/index.json`. No such asset is adopted in this change; any
  future adoption lands through a linked issue with its own ownership row, and
  must not couple to downstream runtime behavior.
- **APTL/runtime capture responsibility stays downstream.** Concrete capture and
  inventory workflow implementations remain with APTL (or the consuming
  runtime); this repository does not adopt runtime capture behavior.

No capture or inventory asset is moved, duplicated, or coupled by this decision.
The decision records placement; movement of any specific asset happens only
under its linked follow-up issue.

## Capture Asset Inventory

Capture and inventory responsibilities are recorded with their current owner,
category, and placement decision so future capture work can be placed without
re-opening this decision. Nothing in this table is moved by this change; example
assets are illustrative, not an inventory of files to migrate.

| Capture Responsibility | Example Assets | Current Owner | Category | Placement Decision | Follow-Up |
| --- | --- | --- | --- | --- | --- |
| SDL-semantic capture meaning | participant/evidence capture semantics, runtime-independent capture definitions | Brad-Edwards/aces | ACES-semantic capture responsibility | Stay in ACES core — reference through the published contract, do not redefine | aces#629 |
| Pack-authoring capture support | pack capture-expectation metadata, artifact-boundary and runtime-profile declarations, static capture-reference validation | none (candidate) | Pack-authoring capture support | Adopt here only on a future linked issue; must reuse the `aces_pack_tools` contract and `schemas/index.json` | aces-scenario-packs#14, aces#629 |
| Runtime capture and inventory workflows | inventory collection, range orchestration, attack-path execution, runtime adapters, environment/credential binding | Brad-Edwards/aptl | APTL/runtime capture responsibility | Stay downstream — do not adopt runtime capture behavior here | aptl#589, aptl#591 |

## ACES-Side And Downstream Follow-Ups

Capture responsibilities that are not owned here are tracked by existing
ACES-family planning issues. These are public cross-links, not private state
(see the [documentation scrub policy](scrub-policy.md)).

- `aces#629` — decide ACES authoring and capture tooling boundary for scenario
  packs. Governs SDL-semantic capture meaning that stays in ACES core and the
  boundary for any pack-authoring capture support adopted here.
- `aptl#589` — review APTL ownership for scenario-pack capture workflows.
  Governs the runtime capture and inventory responsibility that stays
  downstream.
- `aptl#591` — split or migrate APTL capture assets that are scenario-pack
  authoring assets. Feeds any future extraction of a portable pack-authoring
  capture-support subset.
- `aces-scenario-packs#14` — capture workflow placement review (companion side);
  this decision.

## Placement Guardrail

No capture or inventory asset is moved, duplicated, or coupled into this
repository before this placement decision and its linked follow-up issue record
a placement for that asset. A "stay in ACES core" or "stay downstream" decision
blocks movement into this repository; an "adopt here" decision authorizes work
in this repository only through a linked issue that records the asset's ownership
row. Any capture-support asset adopted here must reuse the `aces_pack_tools`
tooling contract (stdlib-only static checks, ordinary `argparse` behavior,
sanitized `Finding` output, schema resolution through `schemas/index.json`,
pack-root path containment, and caller-supplied scrub vocabulary) rather than
creating a parallel contract surface, and must not let runtime capture behavior
leak into the scenario-pack contract.
