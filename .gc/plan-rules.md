# Implementation plan rules

Repo-specific rules the `/implement` workflow MUST follow here, in addition to
the generic workflow. Ground Control injects this file into planning via
`.ground-control.yaml` (`rules.plan_rules`).

## Releases & versioning (ADR 0007 — hard requirement)

- **Never hand-edit the version or changelog.** `__version__` in
  `src/aces_scenario_packs/__init__.py` is a committed literal that only
  `tools/release.py` bumps. Do **not** edit `__version__` or `CHANGELOG.md` in a
  feature PR. A PR that does is wrong; drop that change.
- **Add a changelog fragment for every user-visible change.** Create
  `changelog.d/<issue>.<type>.md` (body = one bullet). The fragment **type is the
  release decision** (this is the rubric):
  - `added` / `changed` / `deprecated` → **minor**
  - `security` / `fixed` → **patch**
  - `breaking` / `removed` → **major** (pre-1.0 → minor)
  - One-line test: *"would a consumer of the `aces-scenario-packs` package observe
    this?"* Yes → add a fragment. Repo-internal only (CI, tests, refactors) → no
    fragment, no release.
- **Never add release/tag/publish steps or run towncrier build in a feature PR.**
  Releasing is a separate act: run `python tools/release.py` (computes the version
  from the fragments, writes `__version__`, collates `CHANGELOG.md`), commit on a
  `release/vX.Y.Z` branch, and open a PR to `main`.
- **PR titles MUST be Conventional Commits** — `type: summary`, `type` one of
  `feat fix docs chore refactor test ci build perf style revert`. A required CI
  check (`PR title guard`, `tools/check_pr_title.py`) blocks non-conforming titles
  and bans agent/tool prefixes like `[claude]`/`[codex]`. This keeps history tidy;
  it does **not** drive the version (fragments do).
- **Merge habits:** feature PRs are **squash-merged** into `dev`. `dev`→`main` is
  promoted with a **merge or rebase — never squash**. Promoting `dev`→`main` is
  what publishes the prepared release.

See [ADR 0007](../docs/decisions/adrs/0007-changelog-driven-versioning.md).

## Repository boundary

- This repo **defines and validates** the scenario-pack format; it does not host
  actual scenario packs. Keep changes within that boundary (see
  [`scenario-packs.md`](../docs/scenario-packs.md) and ADR 0001).
