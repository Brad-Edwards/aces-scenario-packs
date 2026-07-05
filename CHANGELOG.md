# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

PRs do **not** edit this file directly. Add a fragment under
[`changelog.d/`](changelog.d/) instead; `towncrier build` collates fragments into
this file at release-prep. See [`changelog.d/README.md`](changelog.d/README.md).

<!-- towncrier release notes start -->

## [0.1.0] - 2026-07-06

### Added

- Initial release: the ACES scenario-pack definition — the layout contract,
  schemas, bundled template, and shared oracle model — together with the
  authoring/validation CLI tools (`aces-pack-validate`, `aces-pack-release`,
  `aces-new-pack`, `aces-pack-issue-skeleton`), published as the installable
  `aces-scenario-packs` package.
