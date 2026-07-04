# Schema Design Guardrails

ASP-0004 will introduce the first machine-readable scenario-pack schemas. Those
schemas must implement the existing scenario-pack contract rather than create a
second contract surface.

## Canonical Inputs

Schema work must build from these incumbents:

- [ACES scenario-pack contract](../contracts/scenario-pack-contract.md) for
  minimum pack shape, optional-layer declaration rules, lifecycle vocabulary,
  and compatibility boundaries.
- [ADR 0001](decisions/adrs/0001-scenario-pack-contract-boundary.md) for the
  ACES core / scenario-pack / downstream-consumer boundary.
- [Provenance ledger design guardrails](provenance-ledger-design-guardrails.md)
  for contract-v1 source, distribution, content-safety, publication-review, and
  consumer-overlay boundaries.
- [Authoring and capture boundary](authoring-boundary.md) for capture and
  inventory workflow ownership limits.
- [Versioning and release policy](versioning.md) for published-schema version
  and compatibility-impact expectations.
- `.gc/plan-rules.md` for schema-index and loadable-fixture requirements.

## Family Boundaries

Each schema family must have a narrow ownership note so related schemas do not
conflate pack contract concerns:

- Pack metadata describes pack identity, pack version, targeted ACES SDL
  contract version, scenario references, lifecycle state, and declared optional
  layers. It does not redefine SDL semantics.
- Compatibility metadata describes the pack's declared ACES and pack-version
  compatibility. It does not encode a downstream consumer's deployment matrix,
  branch rules, labels, or workflow states.
- Provenance metadata records the pack's provenance ledger: first-class source
  rows, per-artifact distribution class, content-safety attestation, publication
  review, and consumer-overlay boundaries. Distribution class is separate from
  runtime visibility, artifact-boundary disposition, lifecycle state,
  scrub/adoption notes, and review status. The ledger must not copy private
  source content, real credentials, operator tokens, private hosts, or customer
  data.
- Artifact-boundary metadata describes which artifacts are authored, generated,
  included, excluded, or consumer-supplied. It must not move capture or
  inventory workflow assets before the ownership issue resolves.
- Runtime-visibility metadata classifies each artifact root by who may see it at
  runtime (participant-visible, operator-only, oracle-only, distribution-
  restricted). It is orthogonal to artifact-boundary disposition, is a contract
  mapping rather than a mandated directory layout, and must not encode downstream
  delivery, scoreboard, or catalog behavior.
- Runtime-profile metadata may describe portable, ACES-native runtime
  expectations needed to understand a pack. It must not require private
  infrastructure or product-specific execution behavior.
- Delivery-bundle metadata describes audience and packaging in portable
  scenario-pack terms. It does not define downstream portal, class-management,
  scoreboard, or release-channel behavior.
- Lifecycle, validation, and release metadata describe pack maturity,
  validation evidence, schema version, release version, compatibility impact,
  and migration notes. Lifecycle states remain the contract's ACES-native pack
  maturity states.

## Cross-Cutting Gates

Schema changes must pass the repository-wide gates before they are treated as
complete:

- The schema index is the source of truth for published schema ids, versions,
  statuses, source/ownership notes, compatibility impact, and fixture links.
- Every new or changed published schema must have a loadable validation fixture
  covered by the repository's Python `unittest` suite.
- Existing structural tests remain the vocabulary and boundary sentinels:
  `tests/test_repository_contract.py`,
  `tests/test_scenario_pack_contract.py`, and
  `tests/test_template_pack_scaffold.py`.
- CI and local completion use `python3 -m unittest discover -s tests` and
  `python3 -m compileall tests`.
- Security review must treat schemas and fixtures as public artifacts: no real
  secrets, customer data, private hosts, operator tokens, or downstream-private
  vocabulary may be introduced.

## Extensibility

Use versioned schema identifiers and family-local definitions so a future
optional layer can add fields without rewriting the base manifest schema. The
base manifest should reference declared capabilities and schema versions; the
layer-specific schema should own the details for that capability.

Do not create a new exception hierarchy, logging convention, CLI contract, or
release workflow as part of ASP-0004 unless validation tooling in a linked issue
requires it. Until then, schema validation coverage belongs in tests and should
surface failures through ordinary test assertions.

## Non-Goals

ASP-0004 does not:

- Move ACES core SDL schemas or redefine SDL semantics.
- Migrate capture or inventory workflow assets.
- Publish downstream runtime integrations.
- Replace the scenario-pack contract with generated schema prose.
- Implement validation or release tooling beyond the minimum fixtures needed to
  prove schemas are loadable.
