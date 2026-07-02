# Scenario Pack Template

A self-contained, ACES-native starting point for a new scenario pack. It mirrors
the minimum pack shape and optional-layer rules in the
[scenario-pack contract](../../contracts/scenario-pack-contract.md) and the
boundary in [ADR 0001](../../docs/decisions/adrs/0001-scenario-pack-contract-boundary.md).
Every non-real value is marked `PLACEHOLDER:` so it is obvious what must be
replaced and impossible to mistake template content for a real pack.

## Contents

- [pack-manifest.md](pack-manifest.md) — identity, ACES SDL contract reference,
  lifecycle state, provenance/compatibility pointer, scenarios, and explicit
  optional-layer declarations.
- [provenance.md](provenance.md) — provenance and compatibility declaration.
- [scenarios/example-scenario.md](scenarios/example-scenario.md) — one
  placeholder scenario definition (at least one is required).

## How to adopt

1. Copy this directory to your pack's location.
2. Replace every `PLACEHOLDER:` value with real content.
3. Pick one lifecycle state (Draft, Candidate, Published, Deprecated, Withdrawn).
4. Declare each optional layer explicitly as `provided` or `not-provided`; a
   directory alone never implies a capability.
5. Add real scenario definitions in ACES SDL; keep SDL semantics owned by ACES
   core.
6. Confirm no downstream catalog names, private hosts, real credentials, or
   product-runtime assumptions remain (see provenance scrub status).

## Validation

This scaffold is validated by `tests/test_template_pack_scaffold.py`, which
enforces the required files, the manifest's minimum shape, placeholder markers,
an ACES-native lifecycle state, explicit optional-layer declarations for every
contract layer, and self-containment. Run it with the repository verification
commands:

```sh
python3 -m unittest discover -s tests
python3 -m compileall tests
```

The published manifest/validation schema and release tooling are tracked
separately (Brad-Edwards/aces-scenario-packs#4 and #5); when they land, point
this template at the published schema instead of the manifest-shape guidance
here.
