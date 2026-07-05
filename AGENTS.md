# Agent Instructions

This repository is the canonical home for the ACES scenario-pack definition,
schemas, template, and authoring/validation tooling. It does not host actual
scenario packs — those live in their own catalog repositories and consume this
package.

## Repository Boundaries

- ACES core semantics (the SDL) live in `Brad-Edwards/aces`.
- The reusable scenario-pack definition, schemas, template, and
  authoring/validation tooling live here.
- Actual scenario packs live in their own catalog repos, not here.
- Don't import downstream catalog names, paths, branch rules, labels, product
  assumptions, or private deployment vocabulary into the canonical docs.

## Verification

Before declaring repository work complete, run (in a venv with `pip install -e .`):

```sh
python -m unittest discover -s tests
aces-pack-validate --repo .
aces-pack-release check --all
python3 -m compileall src tests
```

## Commits & releases

- PR titles MUST be Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`,
  `refactor:`, `test:`, `ci:`, `build:`); a required CI check enforces it.
- The type is the release decision: `feat:`→minor, `fix:`→patch,
  `feat!:`/`BREAKING CHANGE:`→major; docs/chore/test/ci/refactor/build don't
  release. Never hand-edit a version — the git tag is the source of truth.
- Squash-merge feature PRs into `dev`; promote `dev`→`main` with a merge/rebase.
  See `docs/decisions/adrs/0006-conventional-commit-releases.md`.
