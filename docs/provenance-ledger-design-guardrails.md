# Provenance Ledger Design Guardrails

This note constrains the contract-v1 provenance-ledger work tracked by
Brad-Edwards/aces-scenario-packs#21. It is guidance for design review only; the
schema, fixtures, validator code, templates, and migrated content belong in the
implementation issue.

## Contract Shape

The provenance ledger has four independent parts. The implementation must model
each part explicitly instead of deriving one axis from another.

- `sources[]` rows identify where content came from. A row needs a stable source
  id, source kind, license, usage terms, attribution requirement, attribution
  text when attribution is required, and a record of what was used versus
  excluded. Source kinds must cover upstream corpora, frameworks, tools,
  datasets, research, original design, and generated material. Rows are
  references only; they must not copy private source content, credentials,
  private hosts, or customer data.
- Distribution class belongs to every artifact root and answers what may be
  published, redistributed, sold, generated, or kept consumer-specific. It is
  separate from runtime visibility, artifact-boundary disposition, lifecycle
  state, and publication-review status.
- Content-safety attestation is data with named boolean gates: no real malware,
  no real third-party targets, no real credentials, no sensitive data, and an
  offensive-tooling boundary. Validation requires every gate to be true. The
  policy is exclusion of real sensitive content, not classification into a
  weaker publishable tier.
- Publication review is a checklist with per-gate statuses. The minimum gates
  are licensing, attribution, sensitive-data, and offensive-tooling; a
  consumer-overlay gate may be present when overlays exist. Gate status is one
  of pending, approved, or blocked.

Consumer-specific overlays are declared as path-contained roots. An overlay root
must never overlap a base artifact root, so removing the overlay also removes its
source, licensing, distribution, and review claims without changing the base
pack's claims.

## Incumbents To Reuse

The implementation must build on the repository's existing contract and tooling
surfaces:

- `contracts/scenario-pack-contract.md`, ADR 0001, and the repository charter
  for the ACES core / scenario-pack / downstream-consumer boundary.
- `docs/schema-design-guardrails.md`, `schemas/index.json`, and
  `docs/versioning.md` for published schema ownership, versioning, fixture, and
  compatibility-impact gates.
- `docs/runtime-visibility-design-guardrails.md`,
  `schemas/runtime-visibility.v0.schema.json`, and
  `tools/aces_pack_tools/visibility.py` for the precedent that root
  classifications are explicit axes with policy tables and overlap checks.
- `schemas/artifact-boundary.v0.schema.json` and
  `tools/aces_pack_tools.validate` for artifact-root disposition and existing
  pack-validation wiring.
- `docs/tooling-design-guardrails.md`, ADR 0002, and `tools/README.md` for the
  stdlib-only offline tooling contract.
- `aces_pack_tools.schema.SchemaIndex`, `conformance_errors`, `load_json`,
  `resolve_within_root`, `within_root`, and `pack_relative` for schema loading,
  conformance, and path containment.
- `aces_pack_tools.leak.scan_text` / `scan_pack` and caller-supplied denylist
  terms for leak scanning; do not add downstream-private vocabulary to the tool.
- `aces_pack_tools.model.Finding` and the existing `argparse` CLI style for
  sanitized findings, stdout/stderr separation, and ordinary exit codes.
- `docs/scrub-policy.md` and `SECURITY.md` for scrub targets, synthetic pack
  secrets, and real secret exclusion.

## Cross-Cutting Gates

Provenance-ledger validation must pass the same whole-repo gates as existing
pack validation.

- **Schema/index gate**: the provenance schema remains reachable through
  `schemas/index.json`; changed schema keywords must be covered by
  `aces_pack_tools.schema.SUPPORTED_KEYWORDS` and tests, or enforced by a
  family-specific validator.
- **Boundary gate**: the ledger may describe pack source, rights, safety, and
  review claims. It must not redefine ACES SDL semantics, downstream catalog
  policy, private publication workflows, scoreboards, portals, or deployment
  behavior.
- **Axis-separation gate**: distribution class must not be inferred from
  runtime visibility, artifact-boundary disposition, lifecycle state,
  `scrubStatus`, or review status. In particular, the existing
  runtime-visibility `distribution-restricted` tier is not the new distribution
  class axis.
- **Source-reference gate**: artifact-root provenance claims must resolve to
  declared source ids, and attribution text must be present when a declared
  source requires attribution.
- **Content-safety gate**: every named attestation boolean must be true for a
  releasable pack. Failing or incomplete attestations are validation findings,
  not alternate publishable classes.
- **Publication-review gate**: blocked or pending gates must remain distinct
  from failed content-safety gates. Review status describes clearance to
  publish, not whether the content itself is safe.
- **Overlay-containment gate**: every consumer-specific overlay root resolves
  under the pack root, rejects absolute paths, `..` traversal, and symlink
  escapes, and does not overlap a base artifact root.
- **Leak/scrub gate**: provenance records, examples, and fixtures are public
  artifacts. They must not include real credentials, copied private source
  content, customer data, private hosts, or downstream-private vocabulary.
- **Error-envelope gate**: validation and CLI findings must stay pack-relative
  and sanitized. Do not echo source terms, attribution text, file contents,
  matched leak terms, credentials, private hosts, absolute paths, or environment
  values.
- **OS/runtime gate**: treat pack roots and ledger paths as untrusted local
  inputs. Prefer Python file APIs; if a subprocess is ever required, pass argv
  as an argument list and never place secrets or sensitive evidence in argv.

## Extensibility

The extension seams are the ledger policy sets: source kind, distribution class,
attestation gate, publication-review gate, and overlay root policy. Keep those
as schema enums or small declarative validator tables. Adding a future source
kind, review gate, or distribution class should require updating that policy set,
the fixtures, and the focused validator branch, not rewriting artifact-boundary
or runtime-visibility logic.

If provenance overlay overlap checking needs the same subtree semantics as
runtime visibility, promote a shared root-overlap helper instead of forking two
slightly different implementations.

## Non-Goals And Anti-Patterns

- Do not collapse distribution class into runtime visibility, artifact-boundary
  disposition, lifecycle state, `scrubStatus`, or publication-review status.
- Do not treat publication review as a substitute for content-safety
  attestation; both are required and answer different questions.
- Do not make directory names authoritative for distribution class or overlay
  semantics.
- Do not add downstream catalog terms, private paths, product names, branch
  rules, labels, or deployment vocabulary.
- Do not move capture or inventory workflow assets as part of this work.
- Do not create a second schema registry, JSON conformance checker, leak
  scanner, exception hierarchy, logging framework, cache, database, network
  dependency, or release workflow.
- Do not implement state-mutating release automation, GitHub release publishing,
  branch changes, or remote operations under this contract work.
