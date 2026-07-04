# Changelog fragments

Notable changes are recorded here as one fragment per change, then collated into
a release changelog when release automation lands. Brad-Edwards/aces-scenario-packs#5
established this fragment convention; full release automation (tagging, collation)
is still deferred — see [../docs/versioning.md](../docs/versioning.md).

## Naming

`<issue>.<type>.md` (for example `5.added.md`), or `+<slug>.<type>.md` for a
change with no issue. `<type>` is one of `security`, `added`, `changed`,
`deprecated`, `removed`, or `fixed` — the Keep a Changelog categories, aligned
with the SemVer policy in [../docs/versioning.md](../docs/versioning.md).

Each fragment holds a short Keep-a-Changelog-style entry. Fragments accumulate
here until a release collates them; do not edit a top-level `CHANGELOG.md`
directly.
