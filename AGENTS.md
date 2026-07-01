# Agent Instructions

This repository is the ACES companion repository for scenario-pack definition,
authoring guidance, templates, schemas, tooling, examples, and migration
planning.

## Ground Control

- Ground Control project id: `aces-scenario-packs`.
- Read `.ground-control.yaml` before implementation work.
- The repo-local plan rules live at `.gc/plan-rules.md`.
- Requirement UIDs use the `ASP-####` prefix unless a future issue records a
  different accepted scheme.
- Keep GitHub issues and Ground Control requirements linked when work satisfies
  a tracked requirement.

## Repository Boundaries

- Keep ACES core semantics in `Brad-Edwards/aces`.
- Keep reusable scenario-pack structure, pack validation, templates, examples,
  and authoring guidance here.
- Do not move capture or inventory workflow assets here until the ownership
  review issue is resolved.
- Do not import downstream catalog names, paths, branch rules, labels, product
  assumptions, or private deployment vocabulary into canonical docs.

## Verification

Before declaring repository work complete, run:

```sh
python3 -m unittest discover -s tests
python3 -m compileall tests
```

When changing Ground Control metadata, also verify that
`.ground-control.yaml`, `.mcp.json`, and `.gc/plan-rules.md` remain aligned.
