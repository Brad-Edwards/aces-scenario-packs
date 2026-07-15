# `sdl/` — ACES scenario specification

The hydrated scenario specification in [ACES SDL][aces-sdl] form. **Required**
— every pack has SDL.

- `<name>.sdl.yaml` — the scenario environment and participant behavior. Name
  it after the scenario.
- Add a small `<name>-demo-minimal.sdl.yaml` variant if you want a smoke
  variant for fast verification.

Declare attacker behavior with ACES participant semantics: use `agents`,
`behavior_specifications`, and `action_contracts`, plus ACES preconditions,
effects, failure classes, observation boundaries, outcome interpretation rules,
objectives, evidence requirements, and workflows as needed. Prefer ACES module
composition when environment and behavior need reusable overlays; do not create
a second pack-local behavior schema or maintain two hand-copied scenario specs.

Every `*.sdl.yaml` here is parsed and validated *through ACES* by
`aces-pack-validate` (there is no local SDL schema), and each
`flags/placement.yaml` `host` must resolve to a node declared in one of these
documents. Parse success establishes ACES conformance and semantic consistency;
the live reference tests and participant walkthrough demonstrate that the build
realizes the declared behavior. See [ADR 0011][adr-0011].

[aces-sdl]: https://github.com/Brad-Edwards/aces
[adr-0011]: https://github.com/Brad-Edwards/aces-scenario-packs/blob/main/docs/decisions/adrs/0011-require-pinned-aces-sdl-validation.md
