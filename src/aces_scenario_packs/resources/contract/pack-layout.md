# Scenario pack convention

**Scenario-pack contract version:** `1` (transitional local convention)

This directory is the catalog of **scenario packs**. This document is the
authoritative layout convention every pack follows. It refines the package
contract requirement **PEN-0001** ([issue #119][issue]).

Public scenario-pack format authority now belongs in the companion repository
[`Brad-Edwards/aces-scenario-packs`](https://github.com/Brad-Edwards/aces-scenario-packs).
This repo is the private content factory and golden-evidence home: it authors
scenario content, proves that content on live golden ranges, keeps private
validation evidence, and exports packs once they can conform to the central
contract. Until central v1 ships, this document and the local schemas are
ACES's private stand-in convention. Do not extend them to define new public
schema semantics; record mapping and deltas in
[`docs/central-contract-adoption.md`](../docs/central-contract-adoption.md).

> First-pass rule of thumb: **put in what a scenario has, skip what it
> doesn't.** A pack is a declarative bundle plus one known-good reference — it
> is not an engine. When it ships a golden reference build, that build is a
> participant-equivalent runtime proof, not a scoreboard or productized range
> experience.

## What a scenario pack is

A scenario pack is **declarative content + the tooling that built and tested a
reference implementation + documentation.** A pack ships *source material and a
reference*; it does not ship an engine.

A consumer takes what it needs and **decomposes the pack into its own content
system** the way it builds ranges. The pack's job is to give a range builder
everything required to build and verify the scenario *their* way, with a
known-good reference to check against.

| DLC concept | Scenario pack |
|---|---|
| The bundle you download | `scenarios/<name>/` |
| Game content (levels, assets, items) | SDL start state + bespoke assets + flags + challenges |
| "How to install / what it is" | docs: walkthroughs, concepts, lineage, diagrams, attack-path model |
| Reference build the studio ships | AWS golden build + tests + matching walkthrough |
| The engine | **Not in the pack.** The consumer's range system. |

## Layout

```
scenarios/<name>/
  pack.yaml       # identity + provenance metadata (name, version, authors, contents)
  pack.compatibility.yaml # optional product compatibility projection
  sdl/            # start state (+ injects/events/timeline)
  assets/         # bespoke files/content the scenario needs
  flags/          # flag values | generator | instructions, + placement.yaml
  challenges/     # CTF questions, hints, ratings — keyed by flag id
  ctfd/           # CTFd loader (reference)
  build/          # scripts to stand up the golden version in AWS
  tests/          # scripts to run all paths against the golden AWS range
  docs/
    walkthroughs/ # step-by-step, command-by-command — matches tests/
    concepts.md
    lineage.md
    attack-path.md
    provenance-ledger.yaml # REQUIRED source/licensing/safety/publication ledger
    diagrams/
  profiles/       # delivery/audience bundles (guided, unguided, purple, …)
```

A scaffold of this layout, with annotated placeholders, lives in
[`_template/`](_template/). Copy it to start a new pack.

### Pack metadata (`pack.yaml`)

**Required.** A small descriptive record at the pack root that says what the
pack is, who made it, what version it is, and which optional layers it ships.
This is *catalog/provenance* metadata, not a runtime contract — it pins nothing
about how a consumer builds or runs the pack (see
[not in scope](#explicitly-not-in-scope)). See [Placement map](#placement-map)
and [Challenges](#challenges) for the structured contracts; `pack.yaml` is just
the pack's identity. If a pack is created from a GitHub issue with no formal
Ground Control requirement, set `requirement: null` and cite the issue in the
pack README or lineage; never invent a requirement UID.

```yaml
# pack.yaml
name: <name>                     # pack id; matches the directory name
title: "Human-readable title"
version: 0.1.0                    # pack version; bump when content changes
status: draft                    # draft | built | golden
description: "One line: what the scenario is and what the player does."
authors:
  - Name <email>                 # who authored it
license: "© 2026 Example Org. All rights reserved."
requirement: null                # GC requirement UID, or null for issue-only packs
contents:                        # which optional layers ship; required ones are implicit
  flag_layer: false              # flags/ + challenges/ + ctfd/
  reference_triangle: false      # build/ + tests/ + docs/walkthroughs/
  profile_bundles: false         # profiles/ — delivery/audience bundles
```

`status` tracks the pack's maturity: `draft` (SDL/design only), `built` (stands
up somewhere), `golden` (a participant-equivalent verified reference build +
passing tests).
`contents` declares which all-or-nothing optional groups are present, so the
pack self-describes what a consumer will find. `license` carries the pack's
terms so a consumer who takes a single pack à la carte sees them; it defaults to
the repository [`LICENSE`](../LICENSE) and need only be overridden if a pack
ships under different terms.

`pack.yaml` **must** point at `provenance_ledger: docs/provenance-ledger.yaml`
(the [provenance ledger](#provenance-ledger-docsprovenance-ledgeryaml) — the
required source/licensing/safety/publication contract) and **may** point at
`compatibility_manifest: pack.compatibility.yaml`. The compatibility manifest is
the richer product compatibility projection validated by
[`pack-compatibility.schema.yaml`](pack-compatibility.schema.yaml). It does not
replace SDL, topology, scoring, telemetry, profile, build, reset, or CTFd
ledgers. It indexes them for catalog and commercial-package consumers.

### Compatibility manifest (`pack.compatibility.yaml`)

**Optional, but CI-enforced when referenced.** A pack uses
`pack.compatibility.yaml` when it needs a machine-checkable commercial/product
contract beyond identity metadata. The manifest must be static source metadata:
it cannot discover cloud state, call CTFd, run Terraform, emit telemetry, or
store mutable proof.

The compatibility manifest is a local transitional projection until the central
contract supplies its public v1 schema. Treat it as mapping input and delta
evidence for central adoption, not as a local place to finish or fork the public
contract.

The manifest defines:

- **Pack/source projection**: pack name, title, version, maturity status,
  requirement UID when one exists, GitHub issue provenance, and upstream
  references.
- **Runtime/provider profiles**: build/test/walkthrough references for runtime
  profiles such as `local_minimal`, `aws_minimal`, and `aws_full`. These are
  not delivery bundles.
- **Delivery/audience bundles**: guided, unguided, purple-team,
  agent-benchmark, demo, or custom content bundles. These may join to
  `profiles/bundles.yaml` when a pack ships a profile layer.
- **Platform features**: required, optional, planned, or not-shipped features
  such as real AD, Windows hosts, CTFd, C2/callback containment, cloud IAM, OT,
  IoMT, VPN/jump access, controlled egress, or SaaS facsimiles.
- **Artifact boundaries**: explicit participant/public, operator-only,
  oracle-only, commercial, private, and redistributable roots.
- **Assets, scoring, oracle, telemetry, lifecycle, and operator surfaces**:
  references to existing pack-local ledgers and tools, not duplicated truth.
- **Validation**: commands and gates that prove the manifest, pack layout,
  visibility boundaries, profile bundles, scoring/oracle contracts, tests, and
  rehearsal evidence.

Visibility is a contract, not just a directory name. Existing roots remain
valid equivalents:

| Compatibility boundary | Existing roots and equivalents |
|---|---|
| `participant_visible` / `public` | `assets/briefing/`, safe `assets/content/`, `profiles/_shared/`, `profiles/*/participant/`, or an explicit `public/` root |
| `operator_only` | `profiles/*/operator/`, `docs/` operator runbooks, `tests/`, `build/`, `ctfd/`, or an explicit `operator/` root |
| `oracle_only` / `private` | hidden-path docs, scoring/oracle ledgers, proof predicates, `sdl/*oracle*`, `sdl/scoring.yaml`, `sdl/telemetry.yaml`, or an explicit `oracle/` root |
| `commercial` | bundled content a commercial catalog may ship to licensed operators, commonly `profiles/`, `build/`, `tests/`, `ctfd/`, docs, or an explicit commercial export root |

If a pack introduces literal `public/`, `operator/`, `oracle/`, or
`telemetry/` directories, map them in `pack.compatibility.yaml` before content
relies on them. Participant-visible roots are still covered by the repo-wide
leak scan; operator/oracle/private roots may cite hidden state, proof
predicates, and reset internals.

### Provenance ledger (`docs/provenance-ledger.yaml`)

**Required.** Every pack ships a machine-readable provenance ledger and
references it from `pack.yaml` (`provenance_ledger: docs/provenance-ledger.yaml`);
the `aces-pack-validate` gate enforces its
presence and validates it against
[`provenance.schema.yaml`](provenance.schema.yaml). It is the source of truth for
**where content came from, what may be done with it, whether it is safe to ship,
and whether it has been cleared to publish.** `docs/lineage.md` stays human prose
and cites the ledger. A worked example is
[`_template/docs/provenance-ledger.example.yaml`](_template/docs/provenance-ledger.example.yaml).

The provenance schema is also a transitional local gate. It remains required for
private content safety and publication review, and future central exports map
from it rather than bypassing it.

The ledger has four parts:

- **`sources[]`** — every upstream corpus, framework, tool, dataset, research
  report, original design, generated material, or customer overlay as a
  first-class row with a stable `source_id`, `kind`, `license`, `usage`,
  `attribution_required` (+ `attribution` text when true), and what was `used` /
  `excluded`. Covers MITRE CTID, AEL, ATT&CK, Atomic Red Team, CALDERA,
  scenario-specific research, original design, and generated material.
- **`artifacts[]`** — pack-relative roots classified for **distribution**:
  `open`, `redistributable`, `internal-only`, `commercial-only`, `generated`,
  or `customer-specific`. This is the "open vs ACES-only" axis and is
  **separate** from the compatibility manifest's runtime-visibility export
  values (`public`/`operator`/`oracle`/`private`/`commercial`): one says what may
  be published or sold, the other says who sees it at runtime. Artifact rows may
  cite `source_id`s.
- **`content_safety{}`** — the hard boundary, attested as data:
  `no_real_malware`, `no_real_third_party_targets`, `no_real_credentials`,
  `no_sensitive_data`, `offensive_tooling_boundary`. CI requires **all true** —
  the policy is exclusion of real sensitive content, never a weaker class.
- **`review{}`** — publication review modelled as data, not a comment: a
  per-gate checklist covering at least `licensing`, `attribution`,
  `sensitive-data`, and `offensive-tooling` (optionally `customer-overlay`), each
  `pending`/`approved`/`blocked`.

**Customer overlays.** A private customer overlay declares an `overlays[]` slot
with a path-contained `root`; its content is classified `customer-specific` and
lives only under that root. CI enforces that overlay roots never overlap base
artifact roots, so an overlay can be removed without contaminating the base
pack's source, licensing, or redistributability claims — and a base export never
includes customer-specific material.

### Shared validation oracle model

Reusable oracle authoring guidance and fixture validation live in
[`_oracle/`](_oracle/). This directory is shared operator/oracle-only source,
not a scenario pack, and `aces-pack-validate` validates it through
a dedicated shared-oracle gate.

Pack-local files remain the source of truth for a scenario's hidden path and
proof: `docs/attack-path.md`, `docs/scenario-design.md`, `docs/oracle-map.md`,
`sdl/scoring.yaml`, `sdl/objectives.yaml`, `sdl/telemetry.yaml`, or equivalent
ledgers. The shared model normalizes the common shape across packs: canonical
steps, accepted alternates, evidence, prerequisites, failure states, consumer
adapters, and operator or benchmark exports.

Oracle artifacts must stay separate from participant-visible content. A
participant or agent-benchmark export may expose stable objective ids and award
summaries, but never hidden step order, `S-*` success states, proof predicates,
raw evidence, answers, credentials, flags, or next-step hints. CTFd remains a
consumer adapter over validator verdicts; a CTFd solve is not the oracle.

### A. Start state & content (declarative)

- **`sdl/`** — the scenario start state, plus injects / events / timeline if it
  has them. [ACES SDL][aces-sdl] is the authoring format. This is the one
  section every pack has (see [Required vs optional](#required-vs-optional)).
- **`assets/`** — the bespoke files and content the scenario needs: container
  definitions, custom binaries, documents planted on hosts, site content, decks
  and handouts. Anything custom-authored that the start state references lives
  here.

### B. Flags & challenge layer (declarative + the reference loader)

- **`flags/`** — flag **values**, or a **value generator**, or **instructions**
  to produce them, plus the **placement map** (`flags/placement.yaml`) that says
  exactly where each flag goes. See [Placement map](#placement-map).
- **`challenges/`** — the CTF question, hints, and rating (difficulty / points)
  for each flag, keyed by flag id. See [Challenges](#challenges).
- **`ctfd/`** — the reference CTFd loader.

The flag layer is a coupled group: a pack either has flags-and-challenges or it
doesn't (a pure-emulation scenario may have neither).

### C. Reference build & test tooling (the only imperative part)

- **`build/`** — scripts that stand up the **golden version in AWS**. This is
  the reference build a range builder decomposes into their own content system.
- **`tests/`** — scripts that run every path against the **live golden AWS
  range** and confirm each flag. The tests target the golden range, not an
  abstraction.

### D. Documentation & understanding

- **`docs/walkthroughs/`** — step-by-step, command-by-command walkthroughs that
  **match the test paths** (same commands, same expected output, same flag), so
  the walkthrough is the human-readable form of the reference tests.
- **`docs/concepts.md`** — the concepts the scenario involves.
- **`docs/lineage.md`** — where the content and ideas came from.
- **`docs/attack-path.md`** — the attack-path model that makes the scenario
  understandable.
- **`docs/diagrams/`** — technical diagrams.

### E. Delivery profiles (optional)

- **`profiles/`** — the same scenario packaged for different **audiences**:
  guided and unguided participant runs, a purple-team facilitation set, an
  agent-benchmark contract, a demo/presenter path, and so on. A delivery
  profile is a *content bundle*, **not** a runtime topology profile — it never
  redefines how a consumer builds or sizes the range. The structured selection
  contract is `profiles/bundles.yaml` (the canonical manifest), and `pack.yaml`
  carries `contents.profile_bundles: true` plus a thin `profile_bundles:` index
  pointing at it, so a consumer can select a bundle à la carte from the
  manifest.

  Bundles factor shared participant-safe content once (e.g. `profiles/_shared/`)
  and add explicit per-bundle overlays. They keep the
  [visibility boundary](#how-a-consumer-uses-a-pack): participant-facing files
  live under `profiles/<bundle>/participant/` (and `profiles/_shared/`) and are
  leak-scanned exactly like `assets/briefing/`; operator/facilitator-only files
  live under `profiles/<bundle>/operator/` and may cite the hidden oracle. A
  pack ships this layer with a static `profiles/validate_*.py` gate, the same
  way the SDL ledgers ship their validators.

  The standard ACES delivery bundles are:

  | Bundle id | Required artifacts | Optional artifacts | Exposure rule |
  |---|---|---|---|
  | `guided` | Staged objectives, progressive hints, teaching notes or facilitator pacing, and answer checks/checkpoints. | Facilitator prompts, room pacing variants, remediation notes. | Participant files may teach method but must not reveal oracle ids, ordered hidden-path labels, proof predicates, or scoring maps. Facilitator notes are operator-only. |
  | `unguided` | Terse mission brief, participant objectives, rules of engagement, and calibrated scoring reference through the existing scoring/oracle ledgers. | Post-run reveal, debrief notes, rubric summary. | Participant files contain no path hints, staged solution order, or hidden oracle vocabulary. Scoring calibration is operator-only unless expressed as participant-safe objective text. |
  | `purple-team` | Defender injects, detection goals, expected alert references, blue-team tasks, and debrief prompts. | Timeline variants, SIEM query examples, after-action worksheet. | Defender/operator material may reference telemetry and expected alerts, but any red-team handout remains separate and leak-scanned. |
  | `agent-benchmark` | Deterministic task envelope, participant-safe objective contract, no-facilitator run metadata, machine-readable scoring rubric or operator-only scoring map, and telemetry export reference. | Allowed assumptions, timeout/resource policy, replay metadata, result schema. | The agent-facing contract is participant-safe. Any join from public objective ids to oracle states, scoring outcomes, telemetry hooks, raw proof, or answers is operator-only. |
  | `demo` | Shortened path description, scripted reset reference, reduced-resource runtime compatibility, high-signal proof moments, and presenter script. | Fallback script, timing notes, preflight checklist, cleanup note. | A demo may constrain exposed milestones or compatible runtime profiles, but it reuses the existing reset/build/test contracts and never creates a second hidden path or proof oracle. |

  Profile selection changes **content exposure only**. It does not fork the
  scenario topology, planted content, hidden attack path, scoring oracle,
  telemetry hooks, flags, reset semantics, or golden proof. A shortened demo can
  expose fewer beats, and an agent benchmark can expose a deterministic task
  envelope, but both still point back to the same base scenario contract.

  A pack that ships this layer authors, at minimum:

  - `pack.yaml` with `contents.profile_bundles: true` and a thin
    `profile_bundles:` index pointing at `profiles/bundles.yaml`.
  - `profiles/bundles.yaml` with one row per shipped bundle, using stable
    bundle ids, audience, compatible `runtime_profiles`, shared includes,
    participant entrypoints, operator entrypoints, and any benchmark
    objective/scoring join paths.
  - The entrypoint files named by the manifest, placed under
    `profiles/_shared/`, `profiles/<bundle>/participant/`, or
    `profiles/<bundle>/operator/` according to the exposure rule.
  - A pack-local `profiles/validate_*.py` gate and `profiles/tests` suite that
    validates the manifest, pack index, runtime-profile joins,
    participant/operator split, leak scan, and any oracle/scoring joins.
  - When the pack has a compatibility projection, matching
    `pack.compatibility.yaml.delivery_bundles` rows with pack-local manifest,
    participant path, operator path, and validation references.

  The APT29 emulation pack is the concrete example:
  [`apt29/profiles/bundles.yaml`](apt29/profiles/bundles.yaml) declares the five
  standard bundles and
  [`apt29/profiles/validate_profiles.py`](apt29/profiles/validate_profiles.py)
  validates them without deploying the range.

## The reference triangle (build → test → walkthrough)

`build/`, `tests/`, and `docs/walkthroughs/` are one coherent reference, all
pointed at the same **golden AWS range**:

1. `build/` stands the golden up in AWS.
2. `tests/` runs every path against that live golden range and confirms each
   flag.
3. `docs/walkthroughs/` is the command-by-command human version of those same
   paths.

A range builder gets a known-good build, automated verification of it, and a
matching walkthrough — so when they decompose the pack into their own system
(Shifter-style), they have a reference to validate against path-by-path. AWS is
assumed for both the golden build and its tests.

### Participant-equivalent golden ranges

`golden` is a stronger claim than "the operator can prove it with management
access." A golden reference build must stand up from the declared golden build
profile into the participant start state and then be completable from a
participant-accessible execution surface.

That means:

- The golden build itself creates or seeds every required host, identity,
  domain join, service, share, route, tool, artifact, credential, flag, and
  objective state. Rehearsal scripts may verify and observe; they must not be
  the only thing that makes the range playable.
- The documented happy path starts from something a participant can actually
  use: an attacker host, browser terminal, seeded foothold, VPN-accessible jump
  box, or equivalent role-appropriate surface.
- The path is proven without cloud-console actions, SSM/RunCommand shells,
  Terraform outputs, generated passwords, root shells, database consoles, or
  other management-plane shortcuts. Those are acceptable only for provisioning,
  reset, observation, teardown, and operator diagnostics.
- All credentials or derivation steps required by the attack path are present
  in-world as synthetic scenario content. If lateral movement, privilege
  escalation, collection, or exfiltration requires a secret, the participant can
  discover or derive it from the range itself.
- The proof exercises the intended privilege context. A SYSTEM/root/operator
  shell is not evidence that a user-level foothold is playable.

`golden` does **not** require a consumer-grade portal, scoreboard, scoring
engine, class-management UI, or telemetry product. Those remain runtime concerns
owned by consuming ranges. It **does** require that a human can run the
walkthrough command by command from the participant surface and complete the
scenario in the intended role.

### Golden definition of done

Every scenario pack that claims `golden` must carry a concrete checklist at
`docs/golden-readiness-checklist.md`. The checklist is deliberately written with
unchecked `- [ ]` boxes so the final reviewer can copy it into an issue, PR, or
rehearsal report and mark what was actually proven in that run.

The checklist must cover, at minimum:

- [ ] The range applies from a clean checkout using committed pack content.
- [ ] No hidden repo-root `.env`, external file fetch, or undocumented manual
      setup is required, except approved cloud/operator credentials.
- [ ] The declared golden build profile creates the participant start state.
- [ ] The participant entry surface exists, is documented, and is reachable.
- [ ] The full happy path is executed manually from the participant surface,
      command by command.
- [ ] Operator channels such as SSM, Terraform, cloud consoles, generated
      passwords, root/SYSTEM shells, and database consoles are used only for
      provisioning, diagnostics, reset, observation, or teardown.
- [ ] Every required objective, oracle state, flag, and success condition is
      reached from the intended participant privilege context.
- [ ] Negative gates prove objectives/flags are not trivially reachable before
      the required action or privilege.
- [ ] Reset, persistence, survival, or cleanup behavior works where claimed.
- [ ] Automated rehearsal passes against the same golden build profile.
- [ ] The human walkthrough and automated rehearsal agree path-for-path.
- [ ] Durable evidence is committed as a rehearsal report.
- [ ] Teardown is run and verified; no live range resources remain.
- [ ] `pack.yaml.status: golden` is set only after the above proof exists.

### Scenario milestone structure

A new scenario milestone should be structured so the work naturally reaches the
definition of done instead of relying on reviewer memory. Unless a scenario is
explicitly smaller, create or track issues for these slices:

- [ ] Scenario contract and pack skeleton.
- [ ] Topology, assets, and reference-triangle design.
- [ ] Hidden path, affordance ledger, objective oracle, and validation model.
- [ ] Flag, challenge, and reference CTFd layer, when the scenario has scoring.
- [ ] Delivery profile bundles, when the scenario has multiple audiences.
- [ ] Golden build implementation in the declared live infrastructure.
- [ ] Automated live rehearsal for the golden build.
- [ ] Final manual participant walkthrough.
- [ ] Final docs, status, evidence, and teardown reconciliation.

The **final manual participant walkthrough** is its own slice. It is not
subsumed by "tests passed" or "Terraform applied." That slice stands up the
range, enters through the participant surface, works the happy path by hand,
fixes every discovered defect, re-runs the affected manual step, runs automated
rehearsal, tears down, and records exactly what was proven.

## How a consumer uses a pack

À la carte. A consumer takes what it needs — the SDL as a start-state seed, the
assets, the flags + placement, the challenge text — and **bakes it its own
way**. The `build/`, `tests/`, and `ctfd/` are *the reference* — used as-is,
adapted, or discarded. Nothing in the pack presumes how the consumer runs it.

## Required vs optional

A pack puts in what the scenario has. The sections divide into three tiers:

| Tier | Sections | Rule |
|---|---|---|
| **Required** | `pack.yaml`, `sdl/`, `docs/concepts.md`, `docs/attack-path.md` | Every pack. A pack with no identity, no start state, and no way to understand it is not a pack. |
| **Required-if-present** | the flag layer (`flags/` + `challenges/` + `ctfd/`); the reference triangle (`build/` + `tests/` + `docs/walkthroughs/`) | Each group is all-or-nothing. If a pack ships flags it ships their placement and challenge text; if it ships a golden build it ships the tests and the matching walkthrough. |
| **Optional** | `assets/`, `docs/lineage.md`, `docs/diagrams/`, `profiles/`, `pack.compatibility.yaml` | Include when the scenario has them. `profiles/` (delivery bundles) ships its own `profiles/bundles.yaml` manifest + `validate_*.py` gate when present. `pack.compatibility.yaml` is validated when `pack.yaml` references it. |

The **minimum complete pack** is therefore `pack.yaml` + `sdl/` +
`docs/concepts.md` + `docs/attack-path.md`. A pure-emulation scenario with no objectives is complete
without the flag layer; a paper design not yet built is complete without the
reference triangle.

## Placement map

`flags/placement.yaml` is the one structured contract between flags and assets:
it says where every flag value lands. It is a list of entries keyed by a stable
`flag_id` that the [challenges](#challenges) file reuses.

```yaml
# flags/placement.yaml
flags:
  - flag_id: boreas-mail-creds        # stable id; the join key across the pack
    source: value                     # value | generator | instructions
    value: "PEN{exfil_the_mailbox}"   # present when source: value
    host: boreas-mail                 # an asset / host in the SDL start state
    path: /var/mail/j.frost           # where the value lands on that host
    note: planted in the draft folder # optional human note

  - flag_id: scada-override
    source: generator                 # value produced at build time
    generator: build/gen-override.py  # script, relative to the pack root
    host: brain-controller
    path: /opt/brain/override.code

  - flag_id: gitea-deleted-schematic
    source: instructions              # no shippable value; how to produce it
    instructions: docs/walkthroughs/a7-gitea.md#restore-the-schematic
    host: boreas-intranet
    path: /data/git/aurora/schematic.kicad
```

Rules:

- **One entry per flag**, keyed by `flag_id`. The id is the join key to
  `challenges/` and to the walkthroughs.
- **`source` is one of `value` / `generator` / `instructions`.** Exactly one of
  `value` / `generator` / `instructions` is populated to match.
- **`host` names an asset** that exists in the SDL start state; **`path`** is
  where the value lands on it. Together they are the "flag X goes at host/path
  Y" contract.

## Challenges

`challenges/challenges.yaml` holds the player-facing CTF text for each flag,
keyed by the same `flag_id` as the placement map. One entry per flag.

```yaml
# challenges/challenges.yaml
challenges:
  - flag_id: boreas-mail-creds        # joins to flags/placement.yaml
    title: "Mind the Mailbox"
    category: corporate
    difficulty: easy                  # easy | medium | hard | insane
    points: 100
    question: "Frost left himself a note. What does PEN{...} say?"
    hints:                            # ordered; cost is the loader's concern
      - "Dovecot keeps drafts on disk."
      - "Look under /var/mail."
```

Keep the contract minimal and let the loader own presentation: `ctfd/` maps
these fields onto CTFd's own challenge / hint / scoring model. Long prose hints
or per-flag write-ups may live in their own files under `challenges/` and be
referenced from the entry; the YAML index stays the canonical list.

## Build, release & versioning

A pack is packaged for release by the repo-wide, **static and read-only** gate
the `aces-pack-release` gate. It derives release
views from the contracts above — it never stands up a range, calls a cloud/CTFd/
Terraform/Docker API, mutates state, or uploads. It runs in or behind the
existing scenario-content gate (`aces-pack-validate`); a pack is
**releasable** when it ships a `pack.compatibility.yaml` with
`artifact_boundaries`. `polaris/` and packs without a compatibility manifest are
explicit skips, never a silent partial release.

- **Lint (fail fast).** A pack must not advertise a delivery bundle it does not
  ship. Every `pack.compatibility.yaml.delivery_bundles[].status: supported` row
  must agree with `pack.yaml.contents.profile_bundles`, the `pack.yaml`
  `profile_bundles:` index, and `profiles/bundles.yaml` — bundle id present and
  every shared/participant/operator entrypoint and validation reference present
  on disk. `planned` / `not_shipped` rows are honest metadata and need no shipped
  content; they are never packaged as supported.
- **Build (boundary split).** Each `artifact_boundaries` group is staged into its
  own release root — `participant/`, `operator/`, `oracle/`, `commercial/` — so
  participant-visible, operator-only, and oracle-only material are physically
  separated. Every path is containment-checked (`..`, absolute, and
  symlink-escape paths are rejected), and the operator-token leak scan is re-run
  over the staged participant tier so no hidden vocabulary reaches a participant
  artifact.
- **Profile smoke.** Delivery-bundle selection must change participant exposure:
  each supported bundle's participant view (`_shared/` includes + its
  `participant/` entrypoints) is assembled and the views are proven non-identical
  across bundles, with operator entrypoints never resolving under a participant
  root.
- **Release metadata.** `build` emits a versioned `release.yaml` carrying
  `metadata_schema_version`, the pack version (`pack.yaml.version` is the pack
  release version — CI numbers, timestamps, and git SHAs are build provenance,
  not semantic versions), the **Scenario-pack contract version** above plus a
  `sha256` digest of this file, the supported delivery profiles, compatible
  runtime profiles, and a bounded provenance summary (counts and review-gate
  statuses only — never source/review prose or oracle vocabulary).

  This metadata currently pins the transitional local convention. Add central
  contract source/version/digest metadata only after the companion repository
  publishes central v1 and defines the release field shape.

Run it locally exactly as CI does:

```
aces-pack-release check --all          # lint + smoke + build-to-tempdir
aces-pack-release build --pack <pack> --out dist/
aces-pack-release metadata --pack <pack>
```

## Explicitly not in scope

To keep packs declarative and consumer-agnostic, a pack is **not** any of: a
runtime/engine, a "generator" abstraction, a capability-negotiation or adapter
API, a dependency **lockfile** or runtime contract a consumer must satisfy, a
scoreboard, a range portal, class-management UX, or an emitted
telemetry/observability contract. Those are runtime concerns owned by whatever
consumes the pack — not the pack. The golden reference build is the one runtime
proof the pack ships, and it must be participant-equivalent as defined above.

The descriptive `pack.yaml` and the validated compatibility projection are not
runtime engines. `pack.yaml` records what the pack *is* for the catalog and for
humans. `pack.compatibility.yaml` tells a consumer what the pack exposes and
requires, but it still does not build, resolve, score, observe, or run the pack.

## Existing scenarios

`polaris/` predates this convention and uses an earlier shape (`design/`,
`briefing-deck/`, `content-packages/`); it is not retrofitted by the document
that introduced this convention, and migrating it to this layout is separate
per-scenario work. The other packs — `aurora/`, `apt29/`, `fin7-carbanak/` —
follow this convention. New packs start from [`_template/`](_template/).

[issue]: https://github.com/Brad-Edwards/aces-scenario-packs/issues/119
[aces-sdl]: https://github.com/PaloAltoNetworks/shifter
