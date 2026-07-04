# Authoring And Capture Boundary

This repository is expected to own reusable pack-authoring support after the
ownership issues are resolved. It should not automatically own every capture or
inventory workflow.

## Candidate Ownership Split

- ACES core owns SDL semantics, normative schema authority for core SDL
  concepts, and runtime-independent participant/evidence semantics.
- This repository owns pack layout, pack metadata, pack compatibility,
  release packaging, reusable authoring helpers, validation helpers, and
  scenario-pack examples.
- APTL may own runtime-specific capture, range, or attack-path workflow
  implementations when those assets are consumer-specific.

The capture workflow placement question is now decided in
[ADR 0004](decisions/adrs/0004-capture-workflow-placement.md) and the
[capture workflow placement decision](capture-workflow-placement.md): capture
work is split by responsibility (ACES-semantic capture stays in ACES core,
pack-authoring capture support adopts here only on a linked issue, and runtime
capture stays downstream), and no capture asset is moved before its linked
follow-up records a placement.

## Capture Placement Review Guardrails

ASP-0014 must record the capture/inventory ownership decision before any asset
is moved. The decision may keep assets where they are, move a bounded subset, or
split them by responsibility, but it must classify each asset by the
responsibility it actually performs:

- **ACES-semantic capture responsibility** — definitions or checks that change
  SDL participant, evidence, or runtime-independent scenario semantics. These
  belong with ACES core unless the asset only references public pack structure.
- **Pack-authoring capture support** — portable pack guidance, metadata,
  provenance, artifact-boundary declarations, runtime-profile declarations, and
  static validation that help authors describe capture expectations without
  executing capture. These may belong here when they reuse the published
  scenario-pack contract and schema index.
- **APTL/runtime capture responsibility** — concrete inventory collection,
  range orchestration, attack-path execution, runtime adapters, environment
  binding, credentials, private repository state, or product-specific workflow
  behavior. These stay downstream unless a linked ownership issue explicitly
  extracts a portable pack-authoring subset.

The review must prefer a split by responsibility over a split by source
repository when a single workflow mixes semantic definitions, pack metadata, and
runtime execution. The seam for future extension is the responsibility category
plus the affected schema family or tooling gate, not the current file path or
downstream catalog location.

Any capture support adopted here must pass the same cross-cutting gates as
`aces_pack_tools`: schema resolution through `schemas/index.json`, pack-root
path containment for untrusted inputs, caller-supplied scrub vocabulary,
portable `runtime-profile` terms, `artifact-boundary` disposition rules,
sanitized `Finding` output, ordinary `argparse`/exit-code CLI behavior, and the
repository `unittest`/`compileall` verification gates. It must not introduce
duplicate schema registries, duplicate validation logic, a new exception
hierarchy, a logging framework, network services, caches, databases, secret
configuration, or OS-level exposure of tokens in process arguments.

## Authoring Helper Ownership Gates

ASP-0013 decides authoring-helper ownership before code is moved. That decision
record must classify each helper by source path and owner, proposed owner, and
migration decision, then link the ACES-side follow-up when the helper remains in
or affects ACES core. No helper should move here until that ownership record
exists.

Authoring helpers that land here must reuse the tooling contract already used by
`aces_pack_tools`: stdlib-only static checks unless a separate issue accepts a
dependency, ordinary `argparse` CLI behavior, sanitized `Finding`-shaped output,
schema resolution through `schemas/index.json`, pack-root path containment, and
caller-supplied scrub vocabulary. Helpers must not create duplicate schema
registries, duplicate validation logic, a parallel exception hierarchy, a new
logging framework, networked services, caches, or private deployment
configuration.

Ownership decisions should keep the boundary visible: SDL-semantic authoring
belongs with ACES core unless the helper only orchestrates public pack structure;
consumer-specific runtime, capture, inventory, range, or attack-path behavior
belongs downstream unless a linked ownership issue explicitly splits or moves
it. Public pack-authoring helpers belong here only when they can operate on an
untrusted pack root without secrets, network access, private repository state,
or downstream catalog vocabulary.
