# Scenario Packs

A scenario pack is declarative content plus the tooling, docs, and evidence for
a known-good reference implementation. It is not the range engine, scoreboard,
portal, class-management UI, or telemetry product.

This repository is the authoritative home for that format, and is subordinate to
ACES core (`aces-sdl`): it exists to make authoring and shipping ACES scenarios
easier and defines no extensions to ACES semantics
([ADR 0009](decisions/adrs/0009-scenario-packs-subordinate-to-aces.md)). It ships
the layout contract, template, and tooling as package data, so an author
validates against the same version they build against. Packs live in their own
catalog repositories and consume this package; this repo does not host packs.

## Required Shape

Every new pack starts under `scenarios/<name>/` in a catalog repo and follows
the layout contract bundled in the package (`contract/pack-layout.md`):

- `pack.yaml` for identity, provenance, status, and optional-layer inventory.
- `docs/provenance-ledger.yaml` (required) — the machine-readable source,
  licensing, content-safety, publication-review, and customer-overlay contract,
  referenced from `pack.yaml` via `provenance_ledger:`.
- `pack.compatibility.yaml` when a pack needs a validated product/commercial
  compatibility projection over runtime profiles, delivery bundles, platform
  features, artifact boundaries, operator surfaces, and validation gates.
- `sdl/` for the scenario start state and structured scenario definition.
- `assets/` for custom files, planted content, host assets, and briefing assets.
- `flags/`, `challenges/`, and `ctfd/` as an all-or-nothing flag layer.
- `build/`, `tests/`, and `docs/walkthroughs/` as the reference triangle.
- `profiles/` for delivery and audience bundles when the scenario has them.
- `docs/golden-readiness-checklist.md` for milestone planning and final review.

## SDL Validation (through ACES)

`sdl/` holds the scenario start state as one or more `<name>.sdl.yaml` documents
authored in [ACES SDL][aces-sdl]. `aces-pack-validate` parses **every** direct
`sdl/*.sdl.yaml` through ACES (`aces_sdl.parse_sdl_file`, with full semantic
validation) and fails on a pack that ships no start-state document or any
document ACES rejects. SDL is validated *through ACES* — no SDL schema is
restated here, and the local JSON-Schema subset validator never touches SDL.

`aces-sdl` is therefore a hard, exactly-pinned runtime dependency
(`aces-sdl==0.19.1`) rather than an optional one: the gate is fail-closed, so an
optional coupling that skipped SDL when ACES was absent would leave every pack's
most important content unchecked. The exact pin is deliberate while ACES SDL
contracts are `stability: draft`; advancing it requires compatibility tests. This
raises the package's Python floor to match ACES (`>=3.11`). See
[ADR 0011](decisions/adrs/0011-require-pinned-aces-sdl-validation.md).

The validator also enforces the one canonical pack→SDL link: each
`flags/placement.yaml` `host` must resolve to a real `Scenario.nodes` id in at
least one validated SDL document in the pack (the union across a pack's full and
reduced start-state variants). Only `flags[].host` is checked; no SDL reference
is inferred from prose, filenames, or arbitrary keys.

## Status Meanings

- `draft`: design/source only; the full live scenario is not stood up.
- `built`: it stands up somewhere, but the full path has not been proven end to
  end from the participant surface.
- `golden`: the declared live reference build exists, enters participant start
  state, and has participant-equivalent full-path proof.

Do not mark a pack `golden` because management-plane checks pass. Operator
channels are useful for provisioning and diagnostics, but they do not prove the
participant experience.

## Reference Triangle

The reference triangle is one coherent proof surface:

- `build/` stands up the golden range.
- `tests/` runs every required path against that live range.
- `docs/walkthroughs/` is the human-readable, command-by-command version of the
  same path.

The three must agree path-for-path. A mismatch between them is a defect.

## Compatibility Manifest

`pack.yaml` is the catalog entrypoint. When it contains
`compatibility_manifest: pack.compatibility.yaml`, the referenced file is
validated against the bundled `pack-compatibility.schema.yaml` by
`aces-pack-validate`.

The compatibility manifest separates:

- runtime/provider profiles (`local_minimal`, `aws_minimal`, `aws_full`);
- delivery/audience bundles (`guided`, `unguided`, `purple-team`,
  `agent-benchmark`, `demo`);
- participant/public, operator-only, oracle-only, private, and commercial
  artifact boundaries;
- assets, operator surfaces, and validation gates.

It carries **zero extensions to ACES semantics**: scoring, validation-oracle,
telemetry, and lifecycle (reset/rebuild/teardown) are ACES/runtime concerns and
are deliberately not manifest layers ([ADR 0009](decisions/adrs/0009-scenario-packs-subordinate-to-aces.md)).

The manifest indexes existing pack-local files. It is not a runtime engine,
dependency lockfile, provider adapter, scoreboard, telemetry product, or proof
store.

## Provenance Ledger

Every pack ships `docs/provenance-ledger.yaml`, referenced from `pack.yaml`
(`provenance_ledger:`) and validated against the bundled
`provenance.schema.yaml` by `aces-pack-validate`. It is the canonical,
machine-readable record of:

- **`sources[]`** — upstream corpora, frameworks, tooling, datasets, research,
  original design, and generated material, each with a stable id, license,
  usage, and attribution requirement, plus what was used and deliberately
  excluded.
- **`artifacts[]`** — pack-relative roots classified for distribution as `open`,
  `redistributable`, `internal-only`, `commercial-only`, `generated`, or
  `customer-specific`. This open-vs-ACES-only axis is distinct from the
  compatibility manifest's runtime-visibility export values.
- **`content_safety{}`** — mandatory attestations (no real malware, third-party
  targets, credentials, or sensitive data; offensive-tooling boundary), all of
  which CI requires to be true.
- **`review{}`** — a publication-review checklist modelled as data, covering
  licensing, attribution, sensitive-data, and offensive-tooling gates.

Customer overlays are declared as path-contained `overlays[]` slots; their
content is `customer-specific` and may be removed without contaminating the base
pack. `docs/lineage.md` stays human prose and cites the ledger.

The provenance schema is enforced for every pack: it is the content-safety and
publication-review gate, and pack exports carry the ledger rather than bypassing
it.

**ACES is the authority for pack trust.** A scenario pack is a `reusable_scenario`
asset in the ACES reusable-asset trust policy
(`reusable-asset-trust-policy/v1`; ACES ADR-071), which owns pack integrity and
authenticity (`integrity_digest`, `authenticity_signature`,
`provenance_lock_record`, `governance_source`, `artifact_checksum`). Per
[ADR 0009](decisions/adrs/0009-scenario-packs-subordinate-to-aces.md) and
[ADR 0010](decisions/adrs/0010-consume-aces-reusable-asset-trust-policy.md), this
ledger is scoped to pack-domain facts ACES does not define — content-origin
licensing/attribution (`sources[]`), distribution class (`artifacts[]`),
content-safety attestations (`content_safety{}`), publication review (`review{}`),
and customer-overlay containment (`overlays[]`) — and re-defines none of the
ACES-owned trust concepts; those are established by ACES mechanisms
(scenario-snapshot digest, `aces.lock.json`, RegistryTrustPolicy signatures). ACES
schemas are `stability: draft`, so the ledger references the policy now and the
explicit upstream pin lands once ACES marks it stable. The bundled
[layout contract](../src/aces_scenario_packs/resources/contract/pack-layout.md)
carries the full field-by-field mapping.

## Validation Oracles

When a pack ships an oracle layer, keep the hidden contract in
operator/oracle-only pack-local files and map them through the manifest's
`oracle_only` artifact boundary. The shared oracle model bundled in the package defines
the common authoring shape for canonical steps, accepted alternates, evidence,
prerequisites, failure states, consumer adapters, and operator or benchmark
exports.

Validators should be repeatable observers over committed source and digest-safe
evidence references. CTFd, native scoring, operator debriefs, and
agent-benchmark reports consume validator verdicts; they do not replace the
oracle. Participant-facing files must not expose hidden path order, `S-*`
success states, proof predicates, raw evidence, answers, credentials, flags, or
next-step hints.

## Operating Profiles

ACES uses **delivery/audience bundles** for operating profiles:
`guided`, `unguided`, `purple-team`, `agent-benchmark`, and `demo`. These are
content overlays under `profiles/`; they are not runtime/provider profiles.
Selecting a bundle changes which participant, facilitator, defender, benchmark,
or presenter files are exposed. It does not change the base hidden plan,
topology, planted content, flags, reference tests, or golden proof.

The standard bundle responsibilities are:

- `guided`: staged objectives, progressive hints, teaching notes or facilitator
  pacing, and answer checks/checkpoints.
- `unguided`: terse mission brief, participant objectives, rules of engagement,
  and operator-only post-run reveal material.
- `purple-team`: defender injects, detection goals, expected alerts, blue-team
  tasks, and debrief prompts.
- `agent-benchmark`: deterministic task envelope, participant-safe objective
  contract, no-facilitator run metadata, and an operator-only oracle join.
- `demo`: shortened path, scripted reset reference, reduced-resource runtime
  compatibility, high-signal proof moments, and presenter script.

When a pack ships `profiles/`, `pack.yaml` sets `contents.profile_bundles: true`
and points at `profiles/bundles.yaml`; the pack carries the entrypoint files,
a `profiles/validate_*.py` gate, and `profiles/tests`. The compatibility
manifest mirrors the shipped bundle rows in `delivery_bundles` for catalog and
commercial consumers.

## Build, Release & Versioning

Packaging and release verification is the repo-wide, static/read-only gate
`aces-pack-release`, run in/behind the scenario-content gate. It lints
profile-support consistency (a `supported` delivery bundle must actually ship
its content, or the build fails fast), builds a boundary-split release tree
(`participant/`, `operator/`, `oracle/`, `commercial/`) with the participant
tier leak-scanned, smoke-tests that delivery-bundle selection changes
participant exposure, and emits a versioned `release.yaml` (pack version, the
scenario-pack contract version + digest from the bundled contract, supported
profiles, and a bounded provenance summary). A pack is releasable once it ships
a `pack.compatibility.yaml` with `artifact_boundaries`. Run
`aces-pack-release check --all` locally; see the bundled layout contract
(`contract/pack-layout.md`) for the full build/release section.
