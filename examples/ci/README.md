# Consumer CI example

A runnable GitHub Actions workflow that validates an ACES scenario pack with the
static tooling in this repository. It needs no secrets, tokens, or private
repository state — everything it checks out is public.

## Use it

1. Copy [`validate-pack.yml`](validate-pack.yml) into your pack repository at
   `.github/workflows/validate-pack.yml`.
2. Set `PACK_DIR` (in the workflow `env`) to the directory that holds your pack
   records. The `validate` step expects one `<family>.json` record per schema
   family (for example `pack-metadata.json`, `compatibility.json`,
   `release.json`) in that directory.
3. Commit and push. The workflow checks out this repository for the published
   `schemas/index.json` and the `aces_pack_tools` package, then runs the schema
   validation, leak scan, and release cross-check.

## What it runs

- `python3 -m aces_pack_tools validate <PACK_DIR> --schema-index .../schemas/index.json`
- `python3 -m aces_pack_tools leak <PACK_DIR>`
- `python3 -m aces_pack_tools release <PACK_DIR>/release.json --schema-index .../schemas/index.json`
  (only when a `release.json` is present)

Each command exits non-zero on findings, so a validation failure fails the job
with actionable, pack-relative output. Run the same commands locally before you
push; see [tools/README.md](../../tools/README.md) for the full command
reference.
