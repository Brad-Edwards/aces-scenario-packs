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

## Commit messages & releases

PR titles must follow [Conventional Commits](https://www.conventionalcommits.org)
(`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`, `build:`) — a
CI check enforces this. The type drives the release: `feat:`→minor, `fix:`→patch,
`feat!:`/`BREAKING CHANGE:`→major; `docs`/`chore`/`test`/`ci`/`refactor`/`build`
don't release. Feature PRs are squash-merged, so the title *is* the commit — get
it right. Releases are automatic when `dev` is promoted to `main`; you never edit
a version. See [ADR 0006](docs/decisions/adrs/0006-conventional-commit-releases.md).

Changes to the public contract or schemas should include the rationale, the
compatibility impact, and how you validated them. If you're moving content in
from another repository, note the source repo and paths, and any scrub the
content needs before it lands here.
