# ADR 0015 — Attest Python distribution build provenance

- Status: Accepted
- Date: 2026-07-15
- Amends: [ADR 0004](0004-sbom-and-supply-chain.md) and
  [ADR 0008](0008-adopt-release-please.md)

## Context

The release workflow already builds one wheel and one source distribution,
publishes them to PyPI with OIDC trusted publishing, and attaches them to the
GitHub Release. PyPI's PEP 740 attestations cover the PyPI publication surface,
but consumers also need provenance for the same files through GitHub's artifact
attestation service so each downloaded artifact can be checked with
`gh attestation verify`.

This build provenance is distinct from both the CycloneDX component inventory
and scenario-pack provenance. It must not introduce a second pack schema,
validation model, or local signing format.

## Decision

- The canonical `publish` job in `.github/workflows/release-please.yml` attests
  the wheel and sdist produced by its existing build step. It does not rebuild,
  copy, or transform them for attestation.
- Attestation runs after the artifacts exist and before any PyPI publication or
  GitHub Release upload. Failure is release-blocking, so an unattested artifact
  is not knowingly published by this workflow.
- GitHub's build-provenance action is SHA-pinned like every other third-party
  action in the repository. The job grants only the additional
  `attestations: write` permission; its existing `id-token: write` permission
  supplies a short-lived signing identity and remains shared with PyPI trusted
  publishing. No signing key or new long-lived secret is stored.
- The subject selector is the existing `dist/` output boundary and covers both
  distribution files. Acceptance is checked against each file independently
  with `gh attestation verify` and the repository identity.
- GitHub SLSA build provenance, PyPI PEP 740 attestations, and the CycloneDX
  SBOM are complementary records. None substitutes for or embeds another.

## Consequences

- A release fails closed if GitHub cannot create or persist its provenance
  attestation.
- Consumers can verify either distribution file against the GitHub repository,
  while PyPI continues to produce its own publication attestations.
- A future SBOM attestation must use the SBOM predicate path explicitly; the
  build-provenance subject selector must not be widened to treat the SBOM as a
  Python distribution artifact.
- Static workflow checks can guard permissions, action pinning, subject scope,
  and ordering, but the acceptance contract still requires verification of the
  artifacts from an actual release run.
