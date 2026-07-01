# Branch Protection Expectations

This page records the branching model and the branch-protection expectations for
the ACES scenario-pack companion repository. It documents the intended
server-side configuration; it does not apply it. Configuring GitHub branch
protection is a maintainer action performed with repository admin rights.

## Branching model

- `main` is the released, protected branch. It always reflects shipped state.
- `dev` is the integration branch. Feature work merges here first, then `dev`
  merges to `main` for a release.
- Feature branches are named `<issue-number>-<short-slug>` and are cut from
  `dev`.

The `dev` integration branch exists in this repository.

## Protection expectations

For `main` and `dev`:

- Require a pull request before merging; no direct pushes.
- Require the CI workflow (`.github/workflows/ci.yml`) to pass before merging.
- Require branches to be up to date with the base before merging.
- Keep force-pushes and branch deletion disabled.

Additional expectation for `main`:

- Require at least one approving review before merging a pull request.

## Applying the configuration

These rules are applied through GitHub repository settings or the GitHub API by
a maintainer. This repository does not mutate branch protection from automation,
so the expectations are recorded here as the authoritative reference until they
are configured server-side.
