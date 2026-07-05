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

`<type>` is one of: `security`, `added`, `changed`, `deprecated`, `removed`,
`fixed`. The file body is the bullet text — keep it to one paragraph.

## Build the changelog (at release-prep)

```sh
python -m towncrier build --version <X.Y.Z> --date $(date -u +%F)
```

Preview without writing:

```sh
python -m towncrier build --draft --version <X.Y.Z>
```

Install towncrier with `pip install towncrier` (or `pipx run towncrier` /
`uvx towncrier`). This is decoupled from the release workflow: build + commit the
changelog through the normal PR flow; `python-semantic-release` handles the tag,
PyPI publish, and auto-generated GitHub Release notes separately.
