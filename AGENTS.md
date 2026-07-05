# Agent Instructions

This repository is the canonical home for the ACES scenario-pack definition,
schemas, template, and authoring/validation tooling. It does not host actual
scenario packs.

## Ground Control

- Ground Control project id: `aces-scenario-packs`.
- Read `.ground-control.yaml` before implementation work.
- Requirement UIDs use the `ASP-####` prefix unless a future issue records a
  different accepted scheme.
- Keep GitHub issues and Ground Control requirements linked when work satisfies
  a tracked requirement.

## Repository Boundaries

- Keep ACES core semantics (the SDL) in `Brad-Edwards/aces`.
- Keep the reusable scenario-pack definition, schemas, template, and
  authoring/validation tooling here.
- Do not host actual scenario packs here; they live in their own catalog repos.
- Do not import downstream catalog names, paths, branch rules, labels, product
  assumptions, or private deployment vocabulary into canonical docs.

## Verification

Before declaring repository work complete, run (in a venv with
`pip install -r requirements.txt`):

```sh
python3 -m unittest discover -s scripts/ci/tests
python3 scripts/ci/scenario_content_ci.py
python3 scripts/ci/pack_release.py check --all
python3 -m compileall scripts scenarios
```

When changing Ground Control metadata, also verify that
`.ground-control.yaml` and `.mcp.json` remain aligned.
