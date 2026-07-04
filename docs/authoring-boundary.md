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

The open capture workflow placement issue should decide whether capture assets
are moved, referenced, or split by boundary.

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
