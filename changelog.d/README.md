# Changelog Fragments

Every PR with a user-visible change adds one Markdown fragment in this
directory. `towncrier build` collates the fragments into
[`../CHANGELOG.md`](../CHANGELOG.md) and removes the consumed files. This avoids
merge conflicts from multiple PRs editing the top of `CHANGELOG.md`.

"User-visible" means a consumer of the `aces-scenario-packs` package would notice
it (the contract, schemas, template, or the CLI tools). Repo-internal changes
(CI, tests, refactors) don't need a fragment.

## Add a fragment

Create one file named:

```text
<issue>.<type>.md
```

`<issue>` is the GitHub issue or PR number. For issue-free entries, prefix a
slug with `+`, e.g. `+fix-typo.fixed.md`, to suppress the issue suffix.

`<type>` is one of `breaking`, `security`, `added`, `changed`, `deprecated`,
`removed`, `fixed`. The file body is the bullet text — keep it to one paragraph.

**The type also decides the version bump** (ADR 0007), so pick it deliberately:

| type | bump |
|---|---|
| `breaking`, `removed` | major (pre-1.0: minor) |
| `added`, `changed`, `deprecated` | minor |
| `security`, `fixed` | patch |

## Cutting a release

Run `tools/release.py` — it computes the next version from these fragments (by
type), writes `__version__`, and collates the fragments into
[`../CHANGELOG.md`](../CHANGELOG.md). Then commit on a `release/vX.Y.Z` branch and
open a PR to `main`; merging it tags and publishes that exact version.

```sh
python tools/release.py           # bump __version__ + build CHANGELOG.md
# then: git switch -c release/vX.Y.Z && git commit -am 'chore: release vX.Y.Z'
#       && gh pr create --base main --title 'chore: release vX.Y.Z' --fill
```

Preview the collated section without writing, once you know the version:

```sh
python -m towncrier build --draft --version X.Y.Z
```
