# Authoring And Tooling Ownership Plan

This plan records which scenario-pack authoring helpers this companion repository
owns, which remain with ACES core, and which stay with downstream consumers. It
satisfies ASP-0013 and closes the ownership plan that
[ADR 0002](decisions/adrs/0002-scenario-pack-validation-tooling.md) and
[`tools/README.md`](../tools/README.md) deferred to
Brad-Edwards/aces-scenario-packs#13. The decision is recorded at decision
altitude in [ADR 0003](decisions/adrs/0003-authoring-tooling-ownership.md).

## Purpose

Ownership must be explicit **before** any helper is moved, duplicated, or coupled
across repositories. This plan inventories the authoring and tooling helpers in
scope, assigns each a proposed owner and a migration decision, and links the
ACES-side and downstream follow-ups that track anything not owned here. It
applies the ownership criteria in the
[authoring and capture boundary](authoring-boundary.md) ("Authoring Helper
Ownership Gates"), the [tooling design guardrails](tooling-design-guardrails.md),
and [ADR 0001](decisions/adrs/0001-scenario-pack-contract-boundary.md).

## Helper Categories

Every helper is classified into one category so future helpers can be placed
without re-editing the recorded decisions. The category, not the file name,
drives the ownership default.

- **Pack-structure authoring helper** — scaffolds, generates, or edits public
  pack layout, metadata, provenance, or lifecycle records. Default owner: this
  repository, when it can operate on an untrusted pack root without secrets,
  network access, private repository state, or downstream vocabulary.
- **Validation helper** — static, offline checks of pack structure and metadata
  against the published `schemas/index.json`. Default owner: this repository.
- **Release / packaging helper** — release-record checks and delivery-bundle
  assembly. Static checks belong here; automation that mutates git tags, GitHub
  releases, or remote state is deferred.
- **SDL-semantic helper** — authoring or validation of ACES SDL semantics and
  core participant/evidence meaning. Default owner: ACES core.
- **Downstream runtime / capture helper** — consumer-specific capture, inventory,
  range, attack-path, or runtime behavior. Default owner: downstream (APTL or a
  consumer), unless a linked ownership issue splits or moves it.

## Helper Inventory

Helpers already present in this repository are recorded with their real source
path; helpers that do not yet exist are recorded as candidates so their owner is
decided before any code lands. Nothing in this table is moved by this change.

| Source Path | Current Owner | Category | Proposed Owner | Migration Decision | Follow-Up |
| --- | --- | --- | --- | --- | --- |
| `tools/aces_pack_tools/` (validate, leak, release, schema, model, cli) | aces-scenario-packs | Validation helper | aces-scenario-packs | Keep — already decided by ADR 0002 | — |
| `templates/scenario-pack/` | aces-scenario-packs | Pack-structure authoring helper | aces-scenario-packs | Keep — canonical authoring scaffold | — |
| `examples/ci/` | aces-scenario-packs | Validation helper | aces-scenario-packs | Keep — consumer-facing authoring example | — |
| Pack scaffolding CLI (`init` / `new-pack`) — candidate, not yet present | none | Pack-structure authoring helper | aces-scenario-packs | Adopt here in a future issue; must reuse the `aces_pack_tools` contract | Brad-Edwards/aces-scenario-packs#13 |
| Pack metadata / provenance generators — candidate, not yet present | none | Pack-structure authoring helper | aces-scenario-packs | Adopt here in a future issue; resolve schemas through `schemas/index.json` | Brad-Edwards/aces-scenario-packs#13 |
| ACES SDL authoring / core semantic validators | Brad-Edwards/aces | SDL-semantic helper | Brad-Edwards/aces (stays) | Do not move — ACES core owns SDL semantics | aces#629 |
| ACES CI / reference integration for the companion repo | Brad-Edwards/aces | Downstream runtime / capture helper | Brad-Edwards/aces (coordinate) | Do not move — coordinate integration, do not couple | aces#630 |
| Capture / inventory workflow assets | Brad-Edwards/aptl | Downstream runtime / capture helper | Split by responsibility — see [ADR 0004](decisions/adrs/0004-capture-workflow-placement.md); runtime capture stays downstream, pack-authoring capture support adopts here only on a linked issue | Do not move before the linked follow-up records the asset's placement | aces-scenario-packs#14, aptl#591 |
| State-mutating release automation + boundary-split packaging | none | Release / packaging helper | Deferred — delivery-bundle guidance | Do not adopt until the delivery-bundle issue owns it | aces-scenario-packs#9 |

## ACES-Side And Downstream Follow-Ups

Helpers that are not owned here are tracked by existing ACES-family planning
issues. These are public cross-links, not private state (see the
[documentation scrub policy](scrub-policy.md)).

- `aces#629` — decide ACES authoring and capture tooling boundary for scenario
  packs. Governs the SDL-semantic authoring helpers that remain in ACES core.
- `aces#630` — decide ACES CI and reference integration with the companion repo.
  Governs the integration helper that stays coordinated with ACES core.
- `aptl#591` — split or migrate APTL capture assets that are scenario-pack
  authoring assets. Feeds the capture placement review.
- `aces-scenario-packs#14` — capture workflow placement review (companion side).
- `aces-scenario-packs#9` — delivery and audience bundle guidance; owns the
  deferred boundary-split packaging helper.

## Ownership Guardrail

No helper is moved, duplicated, or coupled into this repository before its
ownership is recorded in the inventory above. A "Keep" or "Adopt here" decision
authorizes work in this repository; a "Do not move" or "Deferred" decision blocks
movement until the linked follow-up issue records a new decision. Helpers adopted
here must reuse the `aces_pack_tools` tooling contract (stdlib-only static checks,
ordinary `argparse` behavior, sanitized `Finding` output, schema resolution
through `schemas/index.json`, pack-root path containment, and caller-supplied
scrub vocabulary) rather than creating a parallel contract surface.
