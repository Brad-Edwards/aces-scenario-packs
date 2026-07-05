# ACES Scenario Packs — Definition & Tooling

The canonical, shared home for the ACES scenario-pack **definition**, schemas,
template, and authoring tools. Actual scenario packs live in their own catalog
repositories and consume this contract; this repo does not host packs.

## Definition

- [Scenario packs — what a pack is](scenario-packs.md)
- Pack layout contract: [`scenarios/README.md`](../scenarios/README.md)
- Schemas: [`scenarios/provenance.schema.yaml`](../scenarios/provenance.schema.yaml),
  [`scenarios/pack-compatibility.schema.yaml`](../scenarios/pack-compatibility.schema.yaml)
- Template pack: [`scenarios/_template/`](../scenarios/_template/)
- Shared oracle model: [`scenarios/_oracle/`](../scenarios/_oracle/)
- [Golden readiness](golden-readiness.md)

## Tools

- [Create a new pack (`new_scenario_pack.py`)](new-pack-script.md)
- [Pack issue skeleton generator](pack-issue-skeleton-script.md)
- Content validation / release gates: [`scripts/ci/`](../scripts/ci/)
