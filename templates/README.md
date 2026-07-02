# Templates

This directory will hold reusable scenario-pack templates after the template
scaffold issue is implemented.

Templates must be self-contained and ACES-native. They should not assume a
specific downstream catalog, portal, branch model, or product runtime.

## Available templates

- [Scenario pack template](scenario-pack/README.md) — a self-contained ACES-native
  starting point that mirrors the scenario-pack contract's minimum shape, with
  explicit `PLACEHOLDER:` markers (ASP-0003).

## Template Scaffold Guardrails

Template content must build from the normative
[scenario-pack contract](../contracts/scenario-pack-contract.md) and
[ADR 0001](../docs/decisions/adrs/0001-scenario-pack-contract-boundary.md).
The template may demonstrate pack structure, manifest placeholders, lifecycle
state selection, provenance placeholders, compatibility declarations, and
optional-layer declaration shape, but it must not redefine ACES SDL semantics or
publish a duplicate schema.

Placeholder content must be explicit and machine-searchable. Use a consistent
`PLACEHOLDER:` marker for non-real names, versions, provenance, scenario
references, credentials, tokens, flags, URLs, and proof material. Synthetic
values are acceptable only when labeled as placeholders and when they cannot be
mistaken for production secrets or private infrastructure.

Validation for a template scaffold should reuse the repository's existing
cross-cutting gates before introducing new tooling:

- `tests/test_repository_contract.py` for repository path and downstream-term
  scrub checks.
- `tests/test_scenario_pack_contract.py` for the contract vocabulary and
  optional-layer rules the template must mirror.
- `.gc/plan-rules.md` for the self-contained-template and placeholder-content
  requirements.

When the schema and validation-tooling issues land, the template should be
parameterized around the published manifest/schema version instead of hardcoding
private catalog names, local paths, runtime labels, or consumer workflow states.
Capture and inventory workflow assets remain out of scope until the ownership
review issue resolves that boundary.
