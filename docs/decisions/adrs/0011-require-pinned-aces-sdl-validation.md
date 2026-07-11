# ADR 0011 — Require pinned ACES SDL validation for scenario packs

- Status: Accepted
- Date: 2026-07-11
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md)

## Context

Every scenario pack requires an `sdl/` start state, but `aces-pack-validate`
does not currently parse those files. Pack-local `sdl/validate_*.py` scripts are
optional authoring checks and cannot establish ACES conformance. The pack-owned
`flags/placement.yaml` contract also says that each `host` resolves to an SDL
start-state node, but the validator does not enforce that join.

ACES publishes the `aces-sdl` package as the authority for SDL structural and
semantic validation. Its public `parse_sdl_file()` API returns the validated
`Scenario`, including the resolved `nodes` mapping and non-fatal advisories. The
current published line is `0.19.1`, declares Python `>=3.11`, and the ACES SDL
contracts remain draft. Making ACES optional would leave the package's required
content unchecked in ordinary installations and would not satisfy the
fail-closed pack contract.

## Decision

`aces-sdl` is a mandatory, exactly pinned runtime dependency while the upstream
SDL contracts are draft. The initial pin is `aces-sdl==0.19.1`; advancing it
requires compatibility tests against this package's validator and template.
The package's Python requirement follows the pinned ACES requirement, currently
Python `>=3.11`. A compatible version range may replace the exact pin only after
ACES publishes a stability and compatibility guarantee that justifies it.

`aces-pack-validate` remains the single catalog-validation entry point. It
parses every direct `sdl/*.sdl.yaml` document through ACES
`parse_sdl_file()` with full semantic validation. A pack with no such document,
or with any document ACES rejects, fails. The local JSON-Schema subset validator
continues to serve only pack-owned schemas; it must not validate SDL, consume a
copied SDL schema, or become a second SDL parser. Pack-local validator scripts
remain additive checks, not ACES-conformance authorities.

The returned ACES `Scenario` objects are retained for pack-to-SDL checks rather
than reloading SDL as generic YAML. A `flags/placement.yaml.flags[].host`
reference resolves when its exact identifier is present in `Scenario.nodes` in
at least one validated SDL document in the pack. This union rule supports a
pack's full and reduced start-state variants without inventing a local notion of
which variant is canonical. A future profile-specific placement contract must
make its target SDL variant explicit; it must not change this rule by filename
guessing.

Only structured references declared by the canonical pack contract are checked.
The current such reference is `flags[].host`. The validator must not infer SDL
references from prose, from arbitrary keys ending in `host` or `entity`, or from
downstream catalog vocabulary. A future pack-owned structured reference is
added explicitly and resolves against the already parsed upstream `Scenario`
section that owns its target concept.

ACES owns SDL error classification. The integration consumes the public
`SDLError` hierarchy and preserves ACES errors as fatal and advisories as
non-fatal; it does not create a parallel exception hierarchy or promote an ACES
advisory to failure. Diagnostics join the existing `failures` aggregation and
CLI exit-status convention. They identify the pack and file and remain bounded;
they must not dump a parsed scenario, raw SDL, flag values, credentials, or
other source payloads into CI output.

## Consequences

- This deliberately expands the runtime dependency and SBOM surface. Existing
  Dependabot updates, CI `pip-audit`, and release CycloneDX generation remain
  the supply-chain controls for ACES and its transitive dependencies.
- SDL root files must pass the same real-path containment discipline as other
  pack reads. ACES itself remains responsible for local-import containment,
  lock/trust validation, digest/signature checks, network bounds, and OCI bundle
  extraction safety; this repository does not implement a second module
  resolver.
- ACES OCI imports can perform allowlisted network reads and populate
  `sdl/.aces/module-cache`. No document content or credentials are passed in
  process arguments, and this package adds no persistence of its own. Catalog
  CI must treat ACES trust-policy changes as security-sensitive input and run
  untrusted contributions without repository secrets.
- The SDL path adds one stdout section to the existing CLI, with bounded
  per-file diagnostics, a final aggregate failure count, and exit status `1` on
  any failure. There is no database, service, controller, or pack-side state in
  this validation path beyond the ACES-owned import cache described above.
- ACES API drift, Python-floor changes, or materially different import side
  effects are reviewed when advancing the exact dependency pin rather than
  being accepted implicitly by a resolver.
