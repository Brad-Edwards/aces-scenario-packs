# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

PRs do **not** edit this file directly. Add a fragment under
[`changelog.d/`](changelog.d/) instead; `towncrier build` collates fragments into
this file at release-prep. See [`changelog.d/README.md`](changelog.d/README.md).

<!-- towncrier release notes start -->

## [0.2.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/aces-scenario-packs-v0.1.0...aces-scenario-packs-v0.2.0) (2026-07-06)


### Features

* add scenario-pack validation and release tooling ([16a5889](https://github.com/Brad-Edwards/aces-scenario-packs/commit/16a588908728faa2f70db892975603c4fa725e38))


### Reverts

* 21 contract-v1 provenance ledger; restore provenance.v0 ([95991af](https://github.com/Brad-Edwards/aces-scenario-packs/commit/95991aff8bd914a8725df8f1eaa3a0d649db4065))
* contract-v1 provenance ledger ([#21](https://github.com/Brad-Edwards/aces-scenario-packs/issues/21)) — content-safety attestation unworkable for live-fire ([5e88f70](https://github.com/Brad-Edwards/aces-scenario-packs/commit/5e88f70a218a00f32ee1a8adb3bd7cb42be0a134))


### Documentation

* add ACES scenario-pack contract (ASP-0002) ([42a524e](https://github.com/Brad-Edwards/aces-scenario-packs/commit/42a524ebacb423729d59d93d9c89c090ce0fa903))
* add documentation scrub policy and migration scrub checklist ([5e705e2](https://github.com/Brad-Edwards/aces-scenario-packs/commit/5e705e274f72051ebc3b43028f1bc07d1a9f0360))
* add template scenario-pack scaffold (ASP-0003) ([e0b6b77](https://github.com/Brad-Edwards/aces-scenario-packs/commit/e0b6b77a24589c0e19aa64878563d4f9776e5f8e))
* add versioning and branch-protection governance for ASP-0001 ([71fe219](https://github.com/Brad-Edwards/aces-scenario-packs/commit/71fe2199e6bbbc13d19b9890c1c3ef9e81981885))
* fix contract reference doc tool paths (aces-pack-validate/release) ([bb8864b](https://github.com/Brad-Edwards/aces-scenario-packs/commit/bb8864b401c169ea7be557a2984bb61c3e628447))
* make current for first release; remove Ground Control from docs ([2af0225](https://github.com/Brad-Edwards/aces-scenario-packs/commit/2af02252c3a1dd1c0cd53e572fe9c1ff447f64fd))
* move scenario-pack definition from penumbra-scenarios ([a376bca](https://github.com/Brad-Edwards/aces-scenario-packs/commit/a376bca03c7c7764717da219adf04e162bf342fc))
* record authoring and tooling ownership plan (ASP-0013) ([622d024](https://github.com/Brad-Edwards/aces-scenario-packs/commit/622d0248119bd604ff970f589a841f8a4431c0ac))
* record capture workflow placement decision for ASP-0014 ([4485f2d](https://github.com/Brad-Edwards/aces-scenario-packs/commit/4485f2d8da6bb147cde913f124cc8040d7ab3ef0))

## [0.1.0] - 2026-07-06

### Added

- Initial release: the ACES scenario-pack definition — the layout contract,
  schemas, bundled template, and shared oracle model — together with the
  authoring/validation CLI tools (`aces-pack-validate`, `aces-pack-release`,
  `aces-new-pack`, `aces-pack-issue-skeleton`), published as the installable
  `aces-scenario-packs` package.
