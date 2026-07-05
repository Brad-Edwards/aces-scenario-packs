# ADR 0004 — SBOM and supply-chain provenance

- Status: Accepted
- Date: 2026-07-05

## Context

This package underpins security-scenario content across the ACES ecosystem.
Consumers (and their own downstream auditors) need to know exactly what a given
release contains and depends on. A Software Bill of Materials (SBOM) is the
standard, machine-readable way to provide that, and it is a prerequisite for
supply-chain review and vulnerability triage.

## Decision

- Every release produces a **CycloneDX** SBOM in JSON format, generated from the
  built distribution and its resolved dependencies (`cyclonedx-py`). CycloneDX is
  chosen for broad tooling support in the security ecosystem.
- The SBOM is:
  - **shipped inside the wheel/sdist** (as package data) so an installed copy is
    self-describing, and
  - **attached to the GitHub Release** alongside the wheel and sdist (ADR 0003).
- The SBOM is generated in the release workflow, not committed to the source
  tree, so it always reflects the actual built artifact.
- Because publishing uses OIDC trusted publishing (ADR 0003), the release also
  carries PyPI's provenance/attestation; the SBOM complements that with the
  component inventory.

## Consequences

- Each published version has a verifiable component inventory a consumer can feed
  into supply-chain and vulnerability tooling.
- The release workflow gains an SBOM-generation step and a dependency on
  `cyclonedx-py` (build-time only, not a runtime dependency of the package).
- Keeping the dependency surface minimal (currently `PyYAML`) keeps the SBOM
  small and the attack surface low; adding a runtime dependency is a deliberate,
  reviewable change reflected in the next release's SBOM.
