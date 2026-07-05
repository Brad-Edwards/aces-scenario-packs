# ADR 0006 — Conventional-commit-driven automatic releases

- Status: Accepted
- Date: 2026-07-05
- Supersedes: [ADR 0005](0005-automatic-release-on-merge-to-main.md)

> **Reusable blueprint.** This ADR is written so other repositories can adopt the
> same release model. Everything below is portable; only the package name
> (`aces-scenario-packs`), the version-file path, and the branch names are
> repo-specific. Copy the four building blocks (versioning, release workflow,
> PR-title gate, repo settings), swap those names, and you have the same
> un-forgettable release pipeline.

## Context

ADR 0005 required a human/agent to hand-edit `__version__` in each PR; merging to
`main` then released. Two problems, both fatal at real velocity:

1. **It gets forgotten.** Bumping a version is a step someone has to remember.
   Agents (and humans) don't, so releases silently never happen.
2. **No rubric.** "Should this PR release? patch or minor?" was a per-PR judgment
   with nothing enforcing an answer.

We want releases that are **inescapable** (not a step anyone performs from
memory) and governed by a **mechanical rubric** (release when a consumer-
observable change ships; hold for internal-only changes).

Constraint that shapes the design: **`main` is branch-protected** (it is the
release branch and the deliberate `dev`→`main` promotion is the release gate).
An automated tool therefore must **not push commits back to `main`** — it may
only create tags. That rules out the file-committing version bump PSR does by
default and points at **tag-driven versioning**.

## Decision

Adopt **Conventional Commits** as the release contract and
**python-semantic-release (PSR)** as the engine. The version and the
release-or-not decision are *derived*, never hand-authored.

### 1. Version source of truth = the git tag (via `hatch-vcs`)

The build reads its version from the latest git tag; there is no version string
to edit or commit. PSR creates the tag; `hatch-vcs` turns it into the built
artifact's version.

```toml
# pyproject.toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/<pkg>/_version.py"   # gitignored
```

The package still exposes `__version__`, sourced from installed metadata:

```python
# src/<pkg>/__init__.py
from importlib.metadata import PackageNotFoundError, version as _version
try:
    __version__ = _version("<dist-name>")
except PackageNotFoundError:
    __version__ = "0.0.0"
```

### 2. PSR config — tag-only, no commit-back

```toml
# pyproject.toml
[tool.semantic_release]
tag_format = "v{version}"
allow_zero_version = true
major_on_zero = false          # pre-1.0: breaking -> minor, not major
build_command = "python -m pip install build && python -m build"

[tool.semantic_release.branches.main]
match = "main"
```

**Gotcha:** `commit`/`push`/`tag`/`changelog` are **not** pyproject keys — putting
`commit = false` here is silently ignored and PSR will try to push a commit to
`main` (rejected by branch protection). Set tag-only mode on the **action
inputs** instead (see §3): `commit: "false"` (no commit → the branch push is a
no-op, nothing is pushed to protected `main`), `push: "true"` (pushes only the
tag — `refs/tags/*` is not branch-protected), `tag: "true"`, `vcs_release:
"true"`, `changelog: "false"` (notes go in the GitHub Release, no committed file).

### 3. Release workflow — `on: push: [main]`

PSR computes the next version from the conventional commits since the last tag,
creates the tag + GitHub Release, runs `build_command`, and the job then attaches
an SBOM and publishes to PyPI via OIDC (no stored token). Skeleton:

```yaml
on:
  push: { branches: [main] }
  workflow_dispatch:
    inputs: { force: { description: "force bump (patch|minor|major)", required: false } }
concurrency: { group: release, cancel-in-progress: false }
permissions: { contents: write, id-token: write }
# steps: checkout(fetch-depth:0)
#        -> python-semantic-release@v10 (id: release) with tag-only inputs:
#             commit: "false", changelog: "false", tag: "true", push: "true", vcs_release: "true"
#        -> if released: setup-python + build SBOM + gh release upload
#        -> if released: pypa/gh-action-pypi-publish (OIDC)
#        -> if released: python-semantic-release/publish-action@v10 (attach dist/*)
# Pin all third-party actions to a full commit SHA.
```

`workflow_dispatch` with `force` bootstraps the very first release (see below)
and is the manual override escape hatch.

### 4. Enforcement — a required CI gate on the PR title

This is what makes it inescapable. A `pull_request` check validates the PR title;
combined with **squash-merge**, the title becomes the one commit on `dev`, so
conventional messages always reach `main`.

Use **one repo-local, stdlib-only validator** as the single policy seam —
`tools/check_pr_title.py` — called by both the workflow and the test suite, so the
policy can't drift between YAML and tests. The workflow checks out the **base
ref** so a PR can't weaken its own guard by editing the checker, reads the title
from `$GITHUB_EVENT_PATH` (untrusted event data — never shell-interpolated), and
needs no third-party action. The validator enforces the Conventional Commit shape
with the type set python-semantic-release parses, and also **bans agent/tool
advertising prefixes** (`[claude]`, `[codex]`, `[openai]`, `[chatgpt]`).

```yaml
# .github/workflows/pr-title.yml
on: { pull_request: { types: [opened, edited, synchronize, reopened] } }
permissions: { contents: read }
# job "PR title guard": checkout base.sha -> setup-python -> python tools/check_pr_title.py
```

Make the **`PR title guard`** check **required** on `dev` (and `main`) so a
non-conforming PR cannot merge — the enforcement does not depend on any agent or
workflow remembering. Keep `tools/check_pr_title.py`'s type list in sync with
`.ground-control.yaml` `workflow.pr_title.types` (the agent-side /implement Step 9
check).

### 5. Repo settings

- `squash_merge_commit_title = PR_TITLE` — the squashed commit subject is the
  (conventional) PR title.
- Feature PRs merge into `dev` with **squash**. `dev`→`main` merges with a
  **merge commit or rebase** (never squash — that would collapse all the
  conventional commits into one and lose the per-change history PSR reads).

## The rubric (what releases vs. holds)

The commit *type* is the decision — no per-PR judgment call:

| Commit / PR type | Releases? | Version bump |
|---|---|---|
| `fix:` | yes | patch |
| `feat:` | yes | minor |
| `feat!:` / `fix!:` / `BREAKING CHANGE:` footer | yes | major (pre-1.0: minor) |
| `docs:` `chore:` `test:` `ci:` `refactor:` `build:` `style:` `perf:`* | no | — |

\* `perf:` releases as patch under some presets; treat "does a consumer observe
it?" as the tie-breaker. **One-line rule: release when a consumer of the package
would observe the change; hold when it is repo-internal.**

At velocity this means: merge freely into `dev`; **promoting `dev`→`main` is the
release act**, and PSR releases exactly the accumulated consumer-visible changes
(or nothing, if the batch was chores/docs only).

## First-release bootstrap (one-time, per repo)

`main` starts with no conventional history, so PSR finds nothing to release on
the first `dev`→`main`. Bootstrap the initial version by running the release
workflow via `workflow_dispatch` with `force: minor` (→ `0.1.0`). PSR
auto-manages every release after that.

## PyPI trusted publishing (per repo)

PyPI OIDC publishing needs a one-time **trusted publisher** registered on PyPI
(no token is stored). Register a *pending publisher* before the first upload:
owner + repo, workflow filename (`release.yml`), environment (`pypi` if the job
sets one). Get the workflow *filename* right — a mismatch 403s only the PyPI step.

## Consequences

- Releases can't be forgotten: they're a consequence of promoting `dev`→`main`,
  computed automatically. Forgetting to bump is impossible — there is nothing to
  bump.
- The rubric is mechanical and enforced: the PR-title gate blocks non-conforming
  PRs, so the release decision is always recorded as a commit type.
- The git tag is the single version source of truth; the build and any consumer
  read the same value.
- `main` stays protected; the tool never pushes commits to it, only tags.
- Cost: two workflow habits (squash feature PRs; merge/rebase the `dev`→`main`
  promotion) and a Conventional-Commit discipline that the CI gate enforces.
