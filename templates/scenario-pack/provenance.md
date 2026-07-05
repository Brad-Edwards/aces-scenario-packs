# Provenance and Compatibility (Template)

This template declares where a pack's content came from and what compatibility
boundary it claims, per the
[scenario-pack contract](../../contracts/scenario-pack-contract.md). Replace every
`PLACEHOLDER:` value with real content before publishing.

## Provenance

- Source: PLACEHOLDER: where this pack's content originated (repository, author, or reference)
- Scrub status: PLACEHOLDER: confirm no downstream catalog names, private hosts, real credentials, or product assumptions remain
- Authored by: PLACEHOLDER: maintainer or team name

## Compatibility

- Targeted ACES SDL contract version: PLACEHOLDER: aces-sdl-vX.Y
- Compatibility boundary: PLACEHOLDER: what this pack owns vs. what ACES core and downstream consumers own
- Known consumers: PLACEHOLDER: optional list, or "none declared"

Compatibility is reasoned about through the targeted SDL contract version and the
pack's own SemVer version. Breaking changes follow ../../docs/versioning.md.
