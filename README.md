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

Releases are **automatic** and driven by
[Conventional Commits](https://www.conventionalcommits.org)
(see [ADR 0006](docs/decisions/adrs/0006-conventional-commit-releases.md)). You
never hand-edit a version — the git tag is the source of truth, and
python-semantic-release computes the next version from commit types:

| Change (commit / PR title) | Releases? | Bump |
| --- | --- | --- |
| `fix:` | yes | patch |
| `feat:` | yes | minor |
| `feat!:` / `BREAKING CHANGE:` | yes | major (pre-1.0: minor) |
| `docs:` `chore:` `test:` `ci:` `refactor:` `build:` | no | — |

Rule of thumb: **release when a consumer would observe the change; hold when it's
repo-internal.** Merge freely into `dev`; **promoting `dev`→`main` cuts the
release** — the workflow tags `v<version>`, builds the sdist + wheel, generates a
CycloneDX SBOM, publishes to PyPI via OIDC, and creates the GitHub Release. A CI
check requires PR titles to be conventional; feature PRs are squash-merged, and
`dev`→`main` uses a merge/rebase (never squash).

Licensed under the MIT License (see [`LICENSE`](LICENSE)).
