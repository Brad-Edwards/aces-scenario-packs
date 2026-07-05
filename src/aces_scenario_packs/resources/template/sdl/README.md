# `sdl/` — start state

The scenario start state in [ACES SDL][aces-sdl] form, plus injects / events /
timeline if the scenario has them. **Required** — every pack has a start state.

- `<name>.sdl.yaml` — the start state. Name it after the scenario.
- Add a small `<name>-demo-minimal.sdl.yaml` variant if you want a smoke
  variant for fast verification.

[aces-sdl]: https://github.com/PaloAltoNetworks/shifter
