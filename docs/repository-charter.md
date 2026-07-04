# Repository Charter

This repository exists to define and support ACES scenario packs as reusable
adoption artifacts.

## Scope

In scope:

- Scenario-pack contract and terminology.
- Pack layout guidance.
- Template pack scaffold.
- Pack metadata, compatibility, provenance, lifecycle, release, and validation
  schemas.
- Static validation and release tooling for packs.
- Oracle, scoring, challenge-adapter, and delivery-bundle guidance.
- Golden or live-reference proof guidance in ACES-native language.
- Safe example packs.
- Migration and adoption guidance for downstream catalogs.

Out of scope until a linked issue resolves ownership:

- Moving ACES core SDL authority.
- Moving downstream runtime integrations.
- Product-specific class management, scoreboard, portal, or delivery-system
  behavior.

Capture and inventory placement is decided in
[ADR 0004](decisions/adrs/0004-capture-workflow-placement.md): capture work is
split by responsibility, so runtime capture stays downstream and only
pack-authoring capture support may be adopted here — through a linked issue that
records the asset's placement.

## Operating Model

The repository starts as a planning and migration scaffold. Bootstrap docs and
tracking issues are allowed before migration begins. Contract text, schemas,
tools, and examples should land through focused issues that record source,
scrub, compatibility, validation, and adoption impact.
