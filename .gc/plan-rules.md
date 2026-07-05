# Implementation plan rules

Repo-specific rules the `/implement` workflow MUST follow here, in addition to
the generic workflow. Ground Control injects this file into planning via
`.ground-control.yaml` (`rules.plan_rules`).

## Releases & versioning (ADR 0006 — hard requirement)

- **Never hand-edit a version.** There is no version string to bump — the version
  is derived from the git tag (`hatch-vcs`). Do **not** add, edit, or "bump"
  `__version__`, a `pyproject` version, or any version file in a PR. A PR that
  edits a version is wrong; drop that change.
- **Never add release/tag/publish steps to a feature PR.** Releases are cut
  automatically by `python-semantic-release` on push to `main`. The feature PR's
  only job is the change itself + a correct Conventional Commit title.
- **PR titles MUST be Conventional Commits** — `type: summary`, where `type` is
  one of `feat fix docs chore refactor test ci build perf style revert`. A
  required CI check (`PR title guard`, backed by `tools/check_pr_title.py`) blocks
  non-conforming titles, so a title cannot merge unless it conforms. Titles must
  also not start with an agent/tool prefix like `[claude]`/`[codex]`. Set a
  conforming title when opening the PR (Step 9).
- **The commit type is the release decision** (this is the rubric):
  - Consumer-observable change (behavior, public API, schema, the bundled
    contract/template) → `feat:` (minor) or `fix:` (patch); breaking →
    `feat!:` / `BREAKING CHANGE:` footer (major; pre-1.0 → minor).
  - Repo-internal only (docs, tests, CI, refactor, chore, build) → those types →
    **no release**.
  - One-line test: *"would a consumer of the `aces-scenario-packs` package
    observe this change?"* Yes → `feat`/`fix`. No → `docs`/`chore`/`test`/…
- **Merge habits:** feature PRs are **squash-merged** into `dev` (the PR title
  becomes the single commit semantic-release reads). `dev`→`main` is promoted
  with a **merge or rebase — never squash** (squashing collapses the commits the
  release reads). Promoting `dev`→`main` is the release act.

See [ADR 0006](../docs/decisions/adrs/0006-conventional-commit-releases.md).

## Repository boundary

- This repo **defines and validates** the scenario-pack format; it does not host
  actual scenario packs. Keep changes within that boundary (see
  [`scenario-packs.md`](../docs/scenario-packs.md) and ADR 0001).
