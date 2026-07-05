# ACES Scenario Packs — Definition & Tooling

The canonical, shared home for the ACES scenario-pack **definition**, schemas,
template, and authoring tools, published as the installable `aces-scenario-packs`
package. Actual scenario packs live in their own catalog repositories and consume
this contract; this repo does not host packs.

## Definition

- [Scenario packs — what a pack is](scenario-packs.md)
- [Golden readiness](golden-readiness.md)
- Layout contract, schemas, template, and shared oracle model ship as package
  data under `src/aces_scenario_packs/resources/`
  (`contract/pack-layout.md`, `schemas/`, `template/`, `oracle/`).
- [Architecture Decision Records](decisions/adrs/)

## Tools

- [Create a new pack (`aces-new-pack`)](new-pack-script.md)
- [Pack issue skeleton generator (`aces-pack-issue-skeleton`)](pack-issue-skeleton-script.md)
- `aces-pack-validate` / `aces-pack-release` — content-validation and release gates.
