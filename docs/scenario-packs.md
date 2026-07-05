# Scenario Packs

A scenario pack is declarative content plus the tooling, docs, and evidence for
a known-good reference implementation. It is not the range engine, scoreboard,
portal, class-management UI, or telemetry product.

## Required Shape

Every new pack starts under `scenarios/<name>/` and follows the layout in
`scenarios/README.md`:

- `pack.yaml` for identity, provenance, status, and optional-layer inventory.
- `docs/provenance-ledger.yaml` (required) — the machine-readable source,
  licensing, content-safety, publication-review, and customer-overlay contract,
  referenced from `pack.yaml` via `provenance_ledger:`.
- `pack.compatibility.yaml` when a pack needs a validated product/commercial
  compatibility projection over runtime profiles, delivery bundles, platform
  features, artifact boundaries, scoring/oracle/telemetry references,
  lifecycle hooks, operator surfaces, and validation gates.
- `sdl/` for the scenario start state and structured scenario definition.
- `assets/` for custom files, planted content, host assets, and briefing assets.
- `flags/`, `challenges/`, and `ctfd/` as an all-or-nothing flag layer.
- `build/`, `tests/`, and `docs/walkthroughs/` as the reference triangle.
- `profiles/` for delivery and audience bundles when the scenario has them.
- `docs/golden-readiness-checklist.md` for milestone planning and final review.


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

`pack.yaml` remains the catalog entrypoint. When it contains
`compatibility_manifest: pack.compatibility.yaml`, the referenced file is
validated against `scenarios/pack-compatibility.schema.yaml` by
`scripts/ci/scenario_content_ci.py`.

The compatibility manifest separates:

- runtime/provider profiles (`local_minimal`, `aws_minimal`, `aws_full`);
- delivery/audience bundles (`guided`, `unguided`, `purple-team`,
  `agent-benchmark`, `demo`);
- participant/public, operator-only, oracle-only, private, and commercial
  artifact boundaries;
- shipped, planned, and not-shipped scoring, oracle, telemetry, reset, rebuild,
  teardown, and operator surfaces.

The manifest indexes existing pack-local files. It is not a runtime engine,
dependency lockfile, provider adapter, scoreboard, telemetry product, or proof
store.

## Provenance Ledger

Every pack ships `docs/provenance-ledger.yaml`, referenced from `pack.yaml`
(`provenance_ledger:`) and validated against
`scenarios/provenance.schema.yaml` by `scripts/ci/scenario_content_ci.py`. It is
the canonical, machine-readable record of:

- **`sources[]`** — upstream corpora, frameworks, tooling, datasets, research,
  original design, and generated material, each with a stable id, license,
  usage, and attribution requirement, plus what was used and deliberately
  excluded.
- **`artifacts[]`** — pack-relative roots classified for distribution as `open`,
  `redistributable`, `internal-only`, `commercial-only`, `generated`, or
  `customer-specific`. This open-vs-internal-only axis is distinct from the
  compatibility manifest's runtime-visibility export values.
- **`content_safety{}`** — mandatory attestations (no real malware, third-party
  targets, credentials, or sensitive data; offensive-tooling boundary), all of
  which CI requires to be true.
- **`review{}`** — a publication-review checklist modelled as data, covering
  licensing, attribution, sensitive-data, and offensive-tooling gates.

Customer overlays are declared as path-contained `overlays[]` slots; their
content is `customer-specific` and may be removed without contaminating the base
pack. `docs/lineage.md` stays human prose and cites the ledger.

## Validation Oracles

When a pack ships an oracle or scoring layer, keep the hidden contract in
operator/oracle-only pack-local files and reference those files from
`pack.compatibility.yaml`. The shared model in `scenarios/_oracle/` defines the
common authoring shape for canonical steps, accepted alternates, evidence,
prerequisites, failure states, consumer adapters, and operator or benchmark
exports.

Validators should be repeatable observers over committed source and digest-safe
evidence references. CTFd, native scoring, operator debriefs, and
agent-benchmark reports consume validator verdicts; they do not replace the
oracle. Participant-facing files must not expose hidden path order, `S-*`
success states, proof predicates, raw evidence, answers, credentials, flags, or
next-step hints.

## Operating Profiles

This convention uses **delivery/audience bundles** for operating profiles:
`guided`, `unguided`, `purple-team`, `agent-benchmark`, and `demo`. These are
content overlays under `profiles/`; they are not runtime/provider profiles.
Selecting a bundle changes which participant, facilitator, defender, benchmark,
or presenter files are exposed. It does not change the base hidden plan,
topology, planted content, scoring oracle, telemetry hooks, reset semantics,
flags, reference tests, or golden proof.

The standard bundle responsibilities are:

- `guided`: staged objectives, progressive hints, teaching notes or facilitator
  pacing, and answer checks/checkpoints.
- `unguided`: terse mission brief, participant objectives, rules of engagement,
  and operator-only calibrated scoring or post-run reveal material.
- `purple-team`: defender injects, detection goals, expected alerts, blue-team
  tasks, and debrief prompts.
- `agent-benchmark`: deterministic task envelope, participant-safe objective
  contract, no-facilitator run metadata, operator-only scoring/oracle join, and
  telemetry export reference.
- `demo`: shortened path, scripted reset reference, reduced-resource runtime
  compatibility, high-signal proof moments, and presenter script.

When a pack ships `profiles/`, `pack.yaml` sets `contents.profile_bundles: true`
and points at `profiles/bundles.yaml`; the pack carries the entrypoint files,
a `profiles/validate_*.py` gate, and `profiles/tests`. The compatibility
manifest mirrors the shipped bundle rows in `delivery_bundles` for catalog and
commercial consumers.

## Build, Release & Versioning

Packaging and release verification is the repo-wide, static/read-only gate
`scripts/ci/pack_release.py`, run in/behind the scenario-content gate. It lints
profile-support consistency (a `supported` delivery bundle must actually ship
its content, or the build fails fast), builds a boundary-split release tree
(`participant/`, `operator/`, `oracle/`, `commercial/`) with the participant
tier leak-scanned, smoke-tests that delivery-bundle selection changes
participant exposure, and emits a versioned `release.yaml` (pack version, the
scenario-pack contract version + digest from `scenarios/README.md`, supported
profiles, and a bounded provenance summary). A pack is releasable once it ships
a `pack.compatibility.yaml` with `artifact_boundaries`. Run
`python3 scripts/ci/pack_release.py check --all` locally; see the "Build, release
& versioning" section of `scenarios/README.md` for the full contract.
