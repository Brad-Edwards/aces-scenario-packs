# ACES Scenario Packs

The canonical, shared home for the **ACES scenario-pack definition** and the
**authoring / validation tooling** that goes with it, published as an installable
Python package so catalogs (and others) consume one version-matched artifact
instead of vendoring the contract.

This repository does **not** host scenario packs. Packs live in their own catalog
repositories and consume this contract.

## Install

```sh
pip install aces-scenario-packs
```

This provides the console tools plus the version-matched schemas and template:

- `aces-pack-validate` — validate a pack catalog's content against the contract.
- `aces-pack-release` — boundary-split build, lint, release, and profile-smoke gate.
- `aces-new-pack` — scaffold a new pack from the bundled template.
- `aces-pack-issue-skeleton` — generate a pack work-issue skeleton.

Run the gates from a catalog repository (the tree containing `scenarios/<pack>/`):

```sh
aces-pack-validate --repo .
aces-pack-release check --all
```

## What's here

- **Definition**
  - [`docs/scenario-packs.md`](docs/scenario-packs.md) — what a scenario pack is.
  - Layout contract + schemas + template ship as package data under
    [`src/aces_scenario_packs/resources/`](src/aces_scenario_packs/resources/)
    (`contract/pack-layout.md`, `schemas/`, `template/`, `oracle/`).
  - [Architecture Decision Records](docs/decisions/adrs/) — purpose, packaging,
    build/release, SBOM.
- **Tools** — the package modules under
  [`src/aces_scenario_packs/`](src/aces_scenario_packs/), exposed as the console
  entry points above.

## Boundary

- **ACES core** owns the Scenario Definition Language (SDL) and its semantics.
- **This repository** owns how a scenario pack is structured, authored,
  validated, and released — plus the tools that enforce it.
- **Downstream catalogs** hold the actual packs and any private runtime,
  delivery, or product integrations.

## Development

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

python -m unittest discover -s tests
aces-pack-validate --repo .
aces-pack-release check --all
```

Build and release are documented in
[ADR 0003](docs/decisions/adrs/0003-build-and-release-model.md): a `v*` tag
triggers the release workflow, which builds the sdist + wheel, generates a
CycloneDX SBOM, publishes to PyPI via OIDC trusted publishing, and cuts a GitHub
Release.

Licensed under the MIT License (see [`LICENSE`](LICENSE)).
