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
