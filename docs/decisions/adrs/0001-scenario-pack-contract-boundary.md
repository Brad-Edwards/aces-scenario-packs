# ADR 0001: Scenario-Pack Contract Boundary

Date: 2026-07-01

Status: Accepted

## Context

ASP-0002 will introduce the first public scenario-pack contract in this
companion repository. That contract needs to be stable enough for templates,
schemas, tooling, and examples to build on without confusing ACES core
semantics, downstream catalog behavior, or unresolved capture workflow
ownership.

## Decision

The scenario-pack contract belongs in this repository as ACES-native pack
structure and adoption guidance. It may describe pack layout, optional pack
layers, pack terminology, lifecycle state vocabulary, compatibility boundaries,
and validation expectations.

The contract must not redefine ACES SDL semantics, move capture or inventory
workflow assets, or encode downstream catalog names, statuses, paths, labels,
product assumptions, branch rules, or runtime behavior into canonical pack
terminology.

Optional layers must be modeled as explicit pack capabilities with their own
applicability and validation expectations, not as implicit downstream catalog
features. The base contract must leave room for future layer-specific schemas
without requiring each future optional layer to rewrite the base pack contract.

## Consequences

- Contract text should land as normative documentation before schemas or tools
  rely on it.
- Any future published schema must follow the schema-index and loadable-fixture
  rule in `.gc/plan-rules.md`.
- Contract examples and templates must remain safe ACES-native artifacts and
  must not require private infrastructure or real credentials.
- Lifecycle states must describe pack maturity or publication state, not
  downstream catalog workflow state.

## Non-Goals

- Define the minimum pack shape itself.
- Define specific lifecycle states.
- Migrate ACES core schemas or SDL semantics.
- Decide capture or inventory workflow ownership.
- Specify downstream runtime, portal, class-management, scoring, or delivery
  integrations.
