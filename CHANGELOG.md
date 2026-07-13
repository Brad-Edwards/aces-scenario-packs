# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

PRs do **not** edit this file directly. Add a fragment under
[`changelog.d/`](changelog.d/) instead; `towncrier build` collates fragments into
this file at release-prep. See [`changelog.d/README.md`](changelog.d/README.md).

<!-- towncrier release notes start -->

## [1.0.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v0.1.0...v1.0.0) (2026-07-12)


### ⚠ BREAKING CHANGES

* validate pack sdl/ through ACES and cross-check flag placement ([#92](https://github.com/Brad-Edwards/aces-scenario-packs/issues/92))

### Features

* strip ACES semantic extensions and add an anti-extension guard ([#91](https://github.com/Brad-Edwards/aces-scenario-packs/issues/91)) ([7892dcf](https://github.com/Brad-Edwards/aces-scenario-packs/commit/7892dcf8bbb46e3d3a704ce34c551deedff33f8d)), closes [#83](https://github.com/Brad-Edwards/aces-scenario-packs/issues/83)
* validate pack sdl/ through ACES and cross-check flag placement ([#92](https://github.com/Brad-Edwards/aces-scenario-packs/issues/92)) ([f7129ea](https://github.com/Brad-Edwards/aces-scenario-packs/commit/f7129eac264793c1fa80f89db59d9f9a88cfb6f6))


### Documentation

* consume ACES reusable-asset trust policy for pack provenance ([#90](https://github.com/Brad-Edwards/aces-scenario-packs/issues/90)) ([dc3f106](https://github.com/Brad-Edwards/aces-scenario-packs/commit/dc3f106e4a87e13f6f652fe87637c13a107bf797))
* establish ACES-subordinate charter (ADR 0009) and align governing docs ([#88](https://github.com/Brad-Edwards/aces-scenario-packs/issues/88)) ([db73b71](https://github.com/Brad-Edwards/aces-scenario-packs/commit/db73b711c0930e4c704dc3bca8efa8316b461d31))

## [0.1.0] - 2026-07-06

### Added

- Initial release: the ACES scenario-pack definition — the layout contract,
  schemas, bundled template, and shared oracle model — together with the
  authoring/validation CLI tools (`aces-pack-validate`, `aces-pack-release`,
  `aces-new-pack`, `aces-pack-issue-skeleton`), published as the installable
  `aces-scenario-packs` package.
