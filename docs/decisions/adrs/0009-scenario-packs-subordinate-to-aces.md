# ADR 0009 — Scenario packs are strictly subordinate to ACES (zero extensions)

- Status: Accepted
- Date: 2026-07-06
- Supersedes: the purpose/boundary charter of
  [ADR 0001](0001-repository-purpose-and-boundary.md)

## Context

[ADR 0001](0001-repository-purpose-and-boundary.md) chartered this repository as
the owner of the scenario-pack **definition and tooling**, and its Decision
section listed, under "owns", *"the schemas (provenance, pack-compatibility) …
[and] the shared oracle model."* The README, `AGENTS.md`, and
`.ground-control.yaml` reinforced this as a **peer / "companion"** relationship
with ACES: three co-equal owners (ACES owns the SDL, this repo owns the pack
format, catalogs own the packs).

That framing was wrong, and it had a concrete cost. "Owning the schemas and the
oracle model" licensed this repo to define **semantic extensions to ACES** —
a bespoke provenance/trust model, a compatibility manifest carrying
`scoring` / `validation_oracle` / `telemetry` / `lifecycle` layers, and an
oracle / "hidden path" model — for concepts that ACES core either already owns
(trust/integrity policy, SDL objectives, conditions, evidence, participant and
attacker behaviour, controlled vocabularies) or has **deliberately excluded from
the ecosystem** (scoring, reward, telemetry as scenario semantics). A pack is a
`reusable_scenario` in ACES's own trust vocabulary; it is not a peer that gets to
invent parallel semantics.

## Decision

This repository is **completely subordinate to ACES core** (the `aces-sdl`
package / `Brad-Edwards/aces`). Concretely:

1. **ACES conformance is the dominating objective.** Where this repository and
   ACES ever diverge, ACES wins and this repository is what changes.
2. **This repository exists to make *using ACES* easier.** It is a thin
   packaging / authoring / validation / release layer that makes ACES scenarios
   easy to structure, ship, and verify. That usability role is its entire reason
   to exist.
3. **Zero extensions to ACES semantics.** This repository owns the scenario-pack
   **structure/layout** and the **authoring/validation/release tooling** — and
   nothing else. It carries and references ACES SDL; it never defines, extends,
   or restates ACES semantics. It is not a peer or "companion" of ACES; it is
   downstream of it.
4. **Consume, don't reinvent.** Where ACES owns a concept — SDL, objectives,
   conditions, evidence, participant/attacker behaviour, the reusable-asset
   trust/integrity policy, controlled vocabularies — this repository consumes it
   from ACES (the published `aces-sdl` corpus) rather than defining its own.
5. **Non-concepts stay out.** Scoring, reward, telemetry, and any
   "validation oracle" / "hidden path" model are not ACES concepts and therefore
   not pack concepts. Validity is demonstrated by specifying attacker behaviour
   in ACES participant semantics; the hydrated SDL is the spec.
6. **The boundary is enforced, not just asserted.** An anti-extension guard in
   the validation tooling fails any pack — or any change to this repository's
   contract/schemas/template — that introduces vocabulary or structure extending
   ACES semantics.

If ACES lacks expressivity a scenario needs, that gap is fixed **upstream in
ACES**, never worked around here.

## Consequences

- The "owns the schemas / oracle model" and peer/"companion" language of ADR 0001
  is superseded. ADR 0001's still-valid parts — single source of truth for the
  pack **layout + tooling**, does not host packs, does not define SDL — carry
  forward under this stricter charter.
- The extensions shipping today (the provenance and pack-compatibility schemas,
  the shared oracle model, and the scoring/telemetry/oracle framing in the
  contract and template) are **non-conformant** and are removed or reworked under
  the **"ACES conformance & ownership boundary"** milestone: consume the ACES
  trust policy (#82), strip extensions + add the anti-extension guard (#83),
  validate `sdl/` through ACES (#84), rework validity to ACES participant/attacker
  semantics (#85), follow ACES schema conventions (#86), and align vocabularies
  to ACES concept-authority (#87).
- The repository's governing and reference docs are corrected to the subordinate
  charter (this ADR is the source of truth; README, `AGENTS.md`,
  `.ground-control.yaml`, `docs/`, and the bundled contract/template are brought
  into line).
- ACES schemas are currently `stability: draft`; consuming them is sequenced
  deliberately and pinned once ACES marks them stable. The charter is fixed now;
  the couplings land as ACES settles.
