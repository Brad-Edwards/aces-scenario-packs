# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

PRs do **not** edit this file directly. Add a fragment under
[`changelog.d/`](changelog.d/) instead; `towncrier build` collates fragments into
this file at release-prep. See [`changelog.d/README.md`](changelog.d/README.md).

<!-- towncrier release notes start -->

## [2.0.2](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v2.0.1...v2.0.2) (2026-07-20)


### Bug Fixes

* **deps:** bump aces-sdl from 0.23.0 to 0.23.1 ([#131](https://github.com/Brad-Edwards/aces-scenario-packs/issues/131)) ([6e65fd7](https://github.com/Brad-Edwards/aces-scenario-packs/commit/6e65fd73a4c879dfd7a4d54a5210ed6052c2a42e))
* reject participant/restricted artifact-boundary overlaps ([#127](https://github.com/Brad-Edwards/aces-scenario-packs/issues/127)) ([56e0eab](https://github.com/Brad-Edwards/aces-scenario-packs/commit/56e0eabc95eb4a4e09303986d1525ce5ae491f4b))


### Documentation

* record release-please signing constraints in ADR 0017 ([#130](https://github.com/Brad-Edwards/aces-scenario-packs/issues/130)) ([d20b5d7](https://github.com/Brad-Edwards/aces-scenario-packs/commit/d20b5d724d03254d94f163e88c083dfda78d090d))

## [2.0.1](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v2.0.0...v2.0.1) (2026-07-17)


### Bug Fixes

* **deps:** bump aces-sdl from 0.21.0 to 0.23.0 ([#123](https://github.com/Brad-Edwards/aces-scenario-packs/issues/123)) ([db7035d](https://github.com/Brad-Edwards/aces-scenario-packs/commit/db7035d190cabe4b847c0e888ebcaddde8da262d))

## [2.0.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v1.2.0...v2.0.0) (2026-07-15)


### ⚠ BREAKING CHANGES

* provenance schema_version is now scenario-pack-provenance/v2 with sources[].kind removed; the scenario-pack contract version is 3; a challenges[].category field is rejected by validation (ADR 0014).
* remove bespoke oracle model ([#109](https://github.com/Brad-Edwards/aces-scenario-packs/issues/109))

### Features

* align pack vocabularies to ACES concept-authority ([#111](https://github.com/Brad-Edwards/aces-scenario-packs/issues/111)) ([e8a20e6](https://github.com/Brad-Edwards/aces-scenario-packs/commit/e8a20e6008406d274a3157291d715f48e296c891))
* discover all supported pack checks ([#117](https://github.com/Brad-Edwards/aces-scenario-packs/issues/117)) ([a8ddd35](https://github.com/Brad-Edwards/aces-scenario-packs/commit/a8ddd35f8bb610facb9c5d3dd19957ac54d6b752))
* remove bespoke oracle model ([#109](https://github.com/Brad-Edwards/aces-scenario-packs/issues/109)) ([6cadaf3](https://github.com/Brad-Edwards/aces-scenario-packs/commit/6cadaf3032515cf82c0419ac420fa7825e2f3fca))


### Bug Fixes

* accept explicit pack validation roots ([#116](https://github.com/Brad-Edwards/aces-scenario-packs/issues/116)) ([74dbac8](https://github.com/Brad-Edwards/aces-scenario-packs/commit/74dbac8da4da3bf95cf523f3a918eaa31a83ab68))
* adopt ACES schema $id namespace and schema_version string form ([#110](https://github.com/Brad-Edwards/aces-scenario-packs/issues/110)) ([7c2f305](https://github.com/Brad-Edwards/aces-scenario-packs/commit/7c2f3054d487b29b4cba38ac331bbdd0c715e873))


### Documentation

* add migration scrub policy ([#108](https://github.com/Brad-Edwards/aces-scenario-packs/issues/108)) ([1913856](https://github.com/Brad-Edwards/aces-scenario-packs/commit/1913856e3988eef5c23c04695b0bf1590c1f8035))

## [1.2.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v1.1.0...v1.2.0) (2026-07-13)


### Features

* add single-pack consumer validation API ([#104](https://github.com/Brad-Edwards/aces-scenario-packs/issues/104)) ([5d73177](https://github.com/Brad-Edwards/aces-scenario-packs/commit/5d73177640052c9f4c5f0afdc89c252c49a37937))
* add single-pack consumer validation API ([#104](https://github.com/Brad-Edwards/aces-scenario-packs/issues/104)) ([fa1383d](https://github.com/Brad-Edwards/aces-scenario-packs/commit/fa1383d0161b0e38e288a04a2a2ff3c0f35f0f62))

## [1.1.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v1.0.0...v1.1.0) (2026-07-13)


### Features

* consume ACES associated-artifact manifests ([#98](https://github.com/Brad-Edwards/aces-scenario-packs/issues/98)) ([2b3f730](https://github.com/Brad-Edwards/aces-scenario-packs/commit/2b3f730d491c8a0e67828ede39912e31ec1010f7))

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
