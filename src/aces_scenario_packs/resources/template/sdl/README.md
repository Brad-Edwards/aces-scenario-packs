# `sdl/` — start state

The scenario start state in [ACES SDL][aces-sdl] form, plus injects / events /
timeline if the scenario has them. **Required** — every pack has a start state.

- `<name>.sdl.yaml` — the start state. Name it after the scenario.
- Add a small `<name>-demo-minimal.sdl.yaml` variant if you want a smoke
  variant for fast verification.

Every `*.sdl.yaml` here is parsed and validated *through ACES* by
`aces-pack-validate` (there is no local SDL schema), and each
`flags/placement.yaml` `host` must resolve to a node declared in one of these
documents. See [ADR 0011][adr-0011].

[aces-sdl]: https://github.com/Brad-Edwards/aces
[adr-0011]: https://github.com/Brad-Edwards/aces-scenario-packs/blob/main/docs/decisions/adrs/0011-require-pinned-aces-sdl-validation.md
