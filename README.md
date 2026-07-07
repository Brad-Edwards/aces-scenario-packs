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

This repository is **subordinate to ACES core** (`aces-sdl`): it exists to make
authoring and shipping ACES scenarios easier, and defines **no extensions** to
ACES semantics
([ADR 0009](docs/decisions/adrs/0009-scenario-packs-subordinate-to-aces.md)).

- **ACES core** owns the Scenario Definition Language (SDL) and all scenario
  semantics. Where ACES owns a concept, packs consume it from ACES.
- **This repository** owns how a scenario pack is structured, authored,
  validated, and released — the layout and the tools that enforce it.
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

Releases are managed by **release-please** — merge-driven, nothing hand-run
(see [ADR 0008](docs/decisions/adrs/0008-adopt-release-please.md)). The version
lives in `pyproject.toml` (`[project].version`) and is bumped by release-please;
`__version__` derives from it. The **Conventional Commit PR title** decides the
bump:

| PR title | Bump |
| --- | --- |
| `feat!:` / `BREAKING CHANGE:` | major (pre-1.0: minor) |
| `feat:` | minor |
| `fix:` / `perf:` | patch |
| `docs:` `chore:` `refactor:` `test:` `ci:` `build:` | no release |

You never edit `CHANGELOG.md` — release-please owns it. As feature PRs land on
`main` (via `dev`), release-please keeps a `chore(main): release X.Y.Z` PR up to
date with the version bump + changelog. **Merge that PR to release:** it tags
`vX.Y.Z`, builds the sdist + wheel, generates a CycloneDX SBOM, publishes to PyPI
via OIDC, and cuts the GitHub Release. (The release PR is opened by the CI token,
so its checks don't auto-run — admin-merge it.) A CI check enforces conventional
PR titles and bans agent-branding prefixes.

Licensed under the MIT License (see [`LICENSE`](LICENSE)).
