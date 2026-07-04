# Provenance and Compatibility (Template)

This template declares where a pack's content came from and what compatibility
boundary it claims, per the
[scenario-pack contract](../../contracts/scenario-pack-contract.md). The
machine-readable record is `provenance.json`, validated against the
[`provenance.v1`](../../schemas/provenance.v1.schema.json) schema; this file is
the human-authoring companion. Replace every `PLACEHOLDER:` value with real
content before publishing.

## Provenance ledger

The provenance ledger has four independent parts. Fill in each — do not derive
one from another.

### Sources

List every source, one row per origin. For each: a stable id, its kind
(upstream corpus, framework, tool, dataset, research, original design, or
generated), license, usage terms, whether attribution is required (and the
attribution text when it is), and what was used versus excluded. Record
references only — never copy private content, real credentials, private hosts,
or customer data.

- Source id: PLACEHOLDER: stable id referenced by artifact roots
- Kind: PLACEHOLDER: one of upstream-corpus / framework / tool / dataset / research / original-design / generated
- License / usage: PLACEHOLDER: license identifier and usage terms
- Attribution: PLACEHOLDER: required? if so, the attribution text to render
- Used vs excluded: PLACEHOLDER: what was used, and what was deliberately excluded

### Distribution class (per artifact root)

Declare, for each artifact root, what may be done with its content when the pack
is distributed. This is separate from runtime visibility (who may see a root at
runtime).

- Artifact root + class: PLACEHOLDER: pack-relative root → one of open / redistributable / internal-only / commercial-only / generated / consumer-specific

A `consumer-specific` root is a removable overlay: it must be path-contained and
must not overlap a base artifact root, so removing it removes its claims without
touching the base pack.

### Content-safety attestation

Every gate must be true to release. The policy is exclusion of real sensitive
content, never a weaker class.

- No real malware / third-party targets / credentials / sensitive data: PLACEHOLDER: confirm all true
- Offensive-tooling boundary respected: PLACEHOLDER: confirm true

### Publication review

Record a status (pending / approved / blocked) per gate. A blocked gate fails
validation. Review status is clearance to publish, not whether content is safe.

- Licensing / attribution / sensitive-data / offensive-tooling: PLACEHOLDER: status per gate
- Consumer-overlay (if overlays exist): PLACEHOLDER: status or omit

### Scrub status

- Scrub status: PLACEHOLDER: confirm no downstream catalog names, private hosts, real credentials, or product assumptions remain
- Authored by: PLACEHOLDER: maintainer or team name

## Compatibility

- Targeted ACES SDL contract version: PLACEHOLDER: aces-sdl-vX.Y
- Compatibility boundary: PLACEHOLDER: what this pack owns vs. what ACES core and downstream consumers own
- Known consumers: PLACEHOLDER: optional list, or "none declared"

Compatibility is reasoned about through the targeted SDL contract version and the
pack's own SemVer version. Breaking changes follow ../../docs/versioning.md.
