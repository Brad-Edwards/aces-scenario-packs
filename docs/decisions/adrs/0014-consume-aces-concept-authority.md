# ADR 0014 — Keep governed concept references in ACES concept-authority

- Status: Accepted
- Date: 2026-07-15
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0011](0011-require-pinned-aces-sdl-validation.md), and
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md)

## Context

The pack contract has two ambiguous local classifications. The challenge
example gives `challenges[].category` an unconstrained value, although a
challenge is participant-facing presentation and not a second behavioral
specification. The provenance ledger requires `sources[].kind` from a local
enumeration that mixes corpora, tools, datasets, authorship, and customer
delivery concerns; examples then use that field to classify ATT&CK and
emulation sources.

ACES publishes its governed concept families, UCO alignment, ATT&CK and ATLAS
tactic sources, and controlled vocabularies under `contracts/concept-authority/`.
In particular, offensive classifications belong to the governed SDL scopes
`behavior_specifications.offensive_behavior_refs` and
`behavior_specifications.ai_offensive_behavior_refs`. The pinned `aces-sdl`
distribution validates those scopes and exposes its contract corpus through
the public `aces_contracts` loaders.

Copying terms into a pack schema would create a second authority that drifts on
every ACES update. Repeating the same classification in challenge or provenance
metadata would also make it unclear whether SDL or the pack-side projection is
the scenario specification.

## Decision

ACES-governed concept references have one semantic home: ACES documents and
contracts carried by the pack. ATT&CK and ATLAS tactic classifications are
authored in the corresponding SDL behavior-specification fields and validated
by the pinned ACES parser. UCO mappings and concept-family authority remain in
the ACES concept-authority corpus; the pack format does not expose a second UCO
or concept-family mapping surface.

The canonical challenge contract does not carry `category`. A CTFd or other
presentation adapter may define display grouping in its own adapter-local
configuration, but that vocabulary is not pack semantics. It must not be
promoted to an ATT&CK/ATLAS classification or copied back into the canonical
challenge shape. The zero-extension guard recognizes only the exact structured
path `challenges/challenges.yaml:challenges[].category` and rejects it; it does
not search prose for the word "category" or infer concepts from arbitrary
fields.

The pack-domain provenance ledger does not carry `sources[].kind`. A source row
records only content-origin, licensing, attribution, and usage facts needed for
pack publication. Merely selecting an ACES-governed tactic does not require a
local source row: ACES owns that authority and provenance. When a pack actually
derives distributable prose, code, or artifacts from ATT&CK, ATLAS, or another
source, the ledger may cite that concrete source for licensing and attribution;
the citation does not become a semantic taxonomy or override ACES.

The remaining local vocabulary is justified by the packaging boundary:

- challenge text and its stable flag join are participant-facing pack content;
- source licensing, attribution, and usage are publication facts;
- artifact distribution classes, content-safety exclusions, publication-review
  gates, and overlay containment govern pack release rather than scenario
  meaning.

Current governed behavior references need no pack-side concept validator: they
already pass through `aces_sdl.parse_sdl()` / `parse_sdl_file()` and ACES's
controlled-vocabulary validation. If a future, genuinely pack-owned structured
field must reference an ACES vocabulary, its validation resolves the vocabulary
by id or governed scope through the public
`aces_contracts.controlled_vocabularies` API from the exactly pinned
distribution. It must not vendor the corpus, generate a local enum, parse
private package paths, fetch authority data at validation time, or introduce a
second exception hierarchy.

Removing either local field is a contract-shape change. The provenance schema
advances to `$id` `scenario-pack-provenance-v2.json` and `schema_version`
`scenario-pack-provenance/v2`; the scenario-pack contract content version
advances from 2 to 3. The existing v1 schema is not silently given new meaning.
The package version remains owned by release-please. Templates, examples, prose,
shared static validation, author CI, release metadata, and regression guards
must describe the same current contract version rather than retaining
compatibility shims or duplicate validation paths.

## Consequences

- Advancing the pinned ACES dependency deliberately advances the governed term
  set without editing a local pack schema. ACES API or corpus drift is reviewed
  at that dependency seam.
- `validate_pack()` remains silent and returns its existing bounded, stable
  error codes. Expected ACES vocabulary failures are reported as SDL-invalid;
  raw input values, upstream exception text, source prose, absolute paths, and
  credentials do not enter the consumer error envelope. Author CI continues to
  render the shared result rather than revalidating the vocabulary. Any read
  needed for the structured challenge guard uses the existing descriptor-
  anchored, no-follow filesystem boundary and validation resource limits; it
  does not add an unbounded author-CI-only parser.
- Concept-authority loading is local, in-process package-data access. This
  decision adds no authentication, environment binding, subprocess argument,
  network request, cache, persistence, or logging surface.
- Release metadata may retain bounded counts and genuinely pack-domain
  classifications, but it does not emit the removed source-kind tally or a new
  projection of ACES terms.
- A pack that needs a concept or term absent from ACES raises that gap upstream.
  Local free text, a local enum, or an `x-` term outside ACES's governed
  extension policy is not a workaround.

## Non-goals

This decision does not change ACES SDL semantics, add technique-level taxonomy
where ACES currently governs tactics, define UCO mappings, create a general
ontology service, or make the provenance ledger an ACES trust/provenance model.
It does not define CTFd product configuration, catalog labels, downstream
migration policy, authentication, authorization, acquisition, storage, or
runtime behavior.
