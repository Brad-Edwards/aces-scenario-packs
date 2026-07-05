# New Pack Script

Use `aces-new-pack` to start a new pack from
`scenarios/_template`.

```sh
aces-new-pack blind-example \
  --title "Blind Example" \
  --description "One line: what the scenario is and what the player does." \
  --issue 123
```

For a Ground Control-backed scenario requirement, also pass the requirement UID:

```sh
aces-new-pack example-range \
  --title "Example Range" \
  --requirement EXR-0001
```

The script:

- validates the pack id as lowercase kebab-case;
- copies `scenarios/_template` into `scenarios/<pack-id>`;
- patches `pack.yaml`, `pack.compatibility.yaml` when present, and the first
  README placeholders;
- preserves the build doctrine and `docs/golden-readiness-checklist.md`;
- refuses to overwrite an existing pack.

After scaffolding, edit the generated `pack.yaml` and
`pack.compatibility.yaml`, replace the README with scenario-specific prose, fill
`sdl/` and `docs/`, and plan the milestone using the generated
golden-readiness checklist.
