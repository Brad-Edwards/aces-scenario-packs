# Runtime Visibility Design Guardrails

This note constrains the contract-v1 runtime-visibility work tracked by
Brad-Edwards/aces-scenario-packs#20. It is guidance for design review only; the
schema, fixtures, validator code, and packaging implementation belong in the
implementation issue.

## Contract Shape

Runtime visibility is a second artifact-root axis, not a replacement for the
existing `artifact-boundary` disposition axis.

- `disposition` continues to answer how an artifact enters the pack boundary:
  `authored`, `generated`, `included`, `excluded`, or `consumer-supplied`.
- `runtimeVisibility` answers who may see a declared artifact root at runtime:
  participant-visible/public, operator-only, oracle-only/private, or
  distribution-restricted.
- A declared artifact root that participates in the pack must be classifiable by
  both axes unless a schema-specific rule explicitly excludes it from release
  staging.
- Visibility is a contract classification over pack-relative roots. It must not
  require literal directory names such as `public/`, `operator/`, or `oracle/`.

## Incumbents To Reuse

The implementation must build on the existing repository contract surfaces:

- `contracts/scenario-pack-contract.md`, ADR 0001, and the repository charter for
  the ACES core / scenario-pack / downstream-consumer boundary.
- `docs/schema-design-guardrails.md` and `schemas/index.json` for published
  schema ownership, versioning, fixture, and loadability gates.
- `docs/tooling-design-guardrails.md`, ADR 0002, and `tools/README.md` for the
  stdlib-only offline tooling contract.
- `docs/scrub-policy.md` and `SECURITY.md` for scrub targets and safe treatment
  of synthetic pack secrets versus real credentials.
- `aces_pack_tools.schema.SchemaIndex`, `conformance_errors`,
  `resolve_within_root`, `within_root`, and `pack_relative` for schema loading,
  schema conformance, and path containment.
- `aces_pack_tools.leak.scan_text` / `scan_pack` and caller-supplied denylist
  terms for leak scanning; do not add downstream-private vocabulary to the tool.
- `aces_pack_tools.model.Finding` and the existing `argparse` CLI style for
  sanitized findings, stdout/stderr separation, and ordinary exit codes.

## Cross-Cutting Gates

Runtime-visibility validation must pass the same whole-repo gates as existing
pack validation:

- **Schema/index gate**: new or changed schema families are reachable only
  through `schemas/index.json`, carry source/ownership/compatibility notes, and
  ship valid and violating fixtures covered by `unittest`.
- **Boundary gate**: the schema may classify pack artifact roots and release
  staging rules, but it must not redefine ACES SDL semantics, downstream
  delivery systems, scoreboards, portals, or class-management behavior.
- **Path-containment gate**: every declared root and every staged output path is
  resolved under the pack root or selected release root. Reject absolute paths,
  `..` traversal, and symlink escapes before reading, scanning, copying, or
  reporting the file.
- **Leak/scrub gate**: participant-visible/public material must be scanned for
  secret-shaped content and configured operator/oracle leak vocabulary. Scan the
  source participant tier and re-run the same check over the staged participant
  release root. Findings must report categories, not matched text.
- **Packaging-boundary gate**: each visibility tier stages into its own release
  root. Operator-only, oracle-only/private, and distribution-restricted material
  must never be copied into the participant-visible/public root.
- **Error-envelope gate**: validation and release findings must stay
  pack-relative and sanitized. Do not echo file contents, matched leak terms,
  credentials, private hosts, absolute paths, or environment values.
- **OS/runtime gate**: treat pack roots and release roots as untrusted local
  inputs. Prefer Python file APIs; if a subprocess is ever required, pass argv
  as an argument list and never place secrets or sensitive evidence in argv.

## Extensibility

The extension seam is the visibility tier and its policy, not the current
directory name. Keep tier behavior in a small declarative table or equivalent
schema-driven structure that can answer:

- whether the tier is participant-visible and therefore leak-scanned;
- which release root the tier stages into;
- whether distribution restrictions affect packaging but not visibility naming;
- which denylist or scan policy is supplied by the caller.

Adding a future tier should require updating the tier enum, schema fixture set,
and policy table, not rewriting artifact disposition logic or duplicating a
validator.

## Non-Goals And Anti-Patterns

- Do not collapse runtime visibility into `disposition`, or rename disposition
  values to imply visibility.
- Do not make directory names authoritative for visibility.
- Do not hard-code downstream catalog terms, private paths, product names,
  branch rules, labels, or deployment vocabulary.
- Do not move capture or inventory workflow assets as part of this work.
- Do not create a second schema registry, JSON conformance checker, leak
  scanner, exception hierarchy, logging framework, cache, database, network
  dependency, or release workflow.
- Do not implement state-mutating release automation, GitHub release publishing,
  branch changes, or remote operations under this contract work.
