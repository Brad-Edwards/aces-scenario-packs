# ACES Scenario Packs

ACES Scenario Packs is the companion repository for defining, authoring,
validating, and packaging ACES-native scenario packs.

This repository is intended to make scenario-pack adoption independent of any
single downstream catalog implementation. It will hold the public pack contract,
templates, schemas, validation tooling, authoring guidance, examples, migration
guides, and workflow notes that help a team build a pack that uses ACES
semantics.

## Current Status

This repository has been bootstrapped for planning and migration tracking. It
does not yet contain the final scenario-pack contract, migrated schemas, migrated
tools, or example packs. Those work items are tracked as GitHub issues in this
repository and in the ACES core repository.

## Repository Boundaries

- ACES core defines the Scenario Definition Language and runtime-independent
  semantic contracts.
- This repository defines how an ACES scenario pack is structured, authored,
  validated, released, and adopted.
- Downstream catalogs consume the pack contract and may add private runtime,
  delivery, class-management, or product integrations outside the canonical pack
  contract.
- Capture and inventory workflows may remain in ACES core, move here, move to
  APTL, or split by responsibility. That boundary is tracked as a planning
  issue before any migration happens.

## Initial Surfaces

- [Repository charter](docs/repository-charter.md)
- [Migration planning](docs/migration-plan.md)
- [Authoring and capture boundary](docs/authoring-boundary.md)
- [Contracts placeholder](contracts/README.md)
- [Schemas placeholder](schemas/README.md)
- [Templates placeholder](templates/README.md)
- [Tools placeholder](tools/README.md)
- [Examples placeholder](examples/README.md)

## Ground Control

This repository is managed as Ground Control project `aces-scenario-packs`.
Agents and maintainers should read `.ground-control.yaml` before doing issue,
requirement, or implementation work.

Local verification:

```sh
python3 -m unittest discover -s tests
python3 -m compileall tests
```
