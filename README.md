# ACES Scenario Packs

The canonical, shared home for the **ACES scenario-pack definition** and the
**authoring / validation tooling** that goes with it. It exists so the pack
contract and tools are a standard resource, independent of any single catalog of
actual packs.

This repository does **not** host scenario packs. Packs live in their own
catalog repositories and consume this contract.

## What's here

- **Definition**
  - [`docs/scenario-packs.md`](docs/scenario-packs.md) — what a scenario pack is.
  - [`scenarios/README.md`](scenarios/README.md) — the pack layout contract.
  - [`scenarios/provenance.schema.yaml`](scenarios/provenance.schema.yaml) and
    [`scenarios/pack-compatibility.schema.yaml`](scenarios/pack-compatibility.schema.yaml) — the schemas.
  - [`scenarios/_template/`](scenarios/_template/) — the template pack an author copies.
  - [`scenarios/_oracle/`](scenarios/_oracle/) — the shared validation-oracle model.
- **Tools** (`scripts/`)
  - `new_scenario_pack.py` — scaffold a new pack from the template.
  - `create_scenario_pack_issue_skeleton.py` — generate a pack work issue skeleton.
  - `ci/scenario_content_ci.py` — content/definition validation gate.
  - `ci/pack_release.py` — boundary-split build, lint, release, and profile-smoke gate.

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
pip install -r requirements.txt

# gates (see .github/workflows/ci.yml)
python3 -m unittest discover -s scripts/ci/tests
python3 scripts/ci/scenario_content_ci.py
python3 scripts/ci/pack_release.py check --all
```

Licensed under the MIT License (see [`LICENSE`](LICENSE)).
