# Contributing

Thanks for helping improve the ACES scenario-pack definition and tooling! Please
open a GitHub issue to discuss a change before moving pack contracts, schemas,
templates, examples, or tools into this repository.

When you work on a change:

- Keep it scoped to the linked issue.
- Preserve the repository boundary described in `README.md` and
  `docs/scenario-packs.md` — this repo defines and validates the pack format; it
  does not host packs.
- Run the verification commands in `AGENTS.md` before opening a PR.
- For a user-visible change, add a changelog fragment under
  [`changelog.d/`](changelog.d/) (see its README) — don't edit `CHANGELOG.md`
  directly.

## Changelog & releases

The version is **driven by the changelog** (ADR 0007), so it can't drift from
`CHANGELOG.md`. The **fragment type** you add decides the bump:
`breaking`/`removed`→major, `added`/`changed`/`deprecated`→minor,
`security`/`fixed`→patch. You never hand-edit a version.

To cut a release, run `python tools/release.py` (it computes the version from the
fragments, writes `__version__`, and collates `CHANGELOG.md`), commit on a
`release/vX.Y.Z` branch, and open a PR to `main`; merging it publishes. See
[ADR 0007](docs/decisions/adrs/0007-changelog-driven-versioning.md).

Separately, PR titles must follow
[Conventional Commits](https://www.conventionalcommits.org) (`feat:`, `fix:`,
`docs:`, `chore:`, …) — a CI check enforces this and bans agent-branding
prefixes. That keeps history tidy; it does **not** drive the version. Feature PRs
are squash-merged, so the title *is* the commit — get it right.

Changes to the public contract or schemas should include the rationale, the
compatibility impact, and how you validated them. If you're moving content in
from another repository, note the source repo and paths, and any scrub the
content needs before it lands here.
