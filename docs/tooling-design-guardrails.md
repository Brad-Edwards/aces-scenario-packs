# Tooling Design Guardrails

ASP-0005 adds reusable validation and release support around the scenario-pack
contract. Tooling must enforce the existing contract surfaces instead of
creating a second definition of a valid pack.

## Canonical Inputs

Tooling work must build from these incumbents:

- [ACES scenario-pack contract](../contracts/scenario-pack-contract.md) for
  minimum pack shape, optional-layer rules, lifecycle vocabulary, and
  compatibility boundaries.
- [ADR 0001](decisions/adrs/0001-scenario-pack-contract-boundary.md) for the
  ACES core / scenario-pack / downstream-consumer ownership split.
- [Schema design guardrails](schema-design-guardrails.md) and
  [`schemas/index.json`](../schemas/index.json) for schema ownership, versions,
  fixtures, and compatibility-impact notes.
- [Versioning and release policy](versioning.md) for release metadata,
  compatibility impact, and tag semantics.
- [Authoring and capture boundary](authoring-boundary.md) for capture and
  inventory workflow limits.
- [Security guidance](../SECURITY.md), the PR template boundary checklist, and
  `.gc/plan-rules.md` for scrub, traceability, and verification gates.
- `.github/workflows/ci.yml` for the repository's public verification shape.

## Required Shape

Validation tooling should share one schema/index loading path with the tests.
If the current test-only JSON Schema subset checker becomes part of user-facing
tooling, promote it into a reusable helper and keep tests pointed at that helper;
do not fork a second checker. If a full JSON Schema dependency is introduced,
pin and document it and keep consumer CI examples installable from public
sources.

Tooling output must be actionable and safe: report the check name, pack-relative
path, schema family or boundary gate, and concise failure reason. Do not dump
whole files, environment variables, tokens, private hostnames, or customer data
into errors, logs, temp files, validation evidence, or release notes.

Command-line behavior should use ordinary process exit codes, `argparse`-style
usage errors, and stderr/stdout separation. Do not add a repository-specific
exception hierarchy, logging framework, daemon, service, cache, database, or
network dependency for static pack checks.

## Cross-Cutting Gates

Every validator or release helper must pass these gates:

- **Schema/index gate** — load schemas only through `schemas/index.json`; do not
  hard-code duplicate schema ids, versions, fixture lists, or family ownership.
- **Boundary gate** — validate pack structure and metadata owned by this
  repository, but do not validate or redefine ACES SDL semantics owned by ACES
  core.
- **Scrub/leak gate** — reject real credentials, private hosts, customer data,
  downstream-private vocabulary, and copied private source content. Synthetic
  training values are allowed only when they are clearly pack content.
- **Profile gate** — runtime profile checks must stay portable and ACES-native,
  matching `runtime-profile.v0`; they must not require private infrastructure or
  product-specific execution behavior.
- **Release/boundary gate** — release and artifact-boundary checks must use the
  `release` and `artifact-boundary` schema families plus `docs/versioning.md`.
  Packaging must exclude consumer-supplied, excluded, and unresolved capture or
  inventory workflow assets unless a linked ownership issue changes that
  boundary.
- **CI gate** — consumer-facing examples must be runnable by external adopters
  without repository secrets, private repository state, Sonar tokens, or Ground
  Control credentials.

## OS And Runtime Guardrails

Tools should treat a pack root as untrusted input. Resolve paths relative to the
pack root, reject traversal outside that root, and avoid following symlinks into
private locations when packaging or scanning. Prefer direct Python file APIs over
shelling out. If a subprocess is unavoidable, pass arguments as arrays and never
place credentials or sensitive evidence in process argv.

Temporary files and generated archives must contain only pack-owned public
artifacts and scrubbed metadata. Release helpers should produce deterministic,
reviewable outputs and avoid mutating Git tags, GitHub releases, branch
protection, or remote state unless a separate issue explicitly owns that
automation.

## Extensibility

The first tooling surface should be parameterized by pack root, schema index
path, selected check set, and output format. New optional layers should register
their schema family and check kind through the schema index or a small
declarative table, not by editing a monolithic validator.

Keep validation evidence shaped so it can populate `validation.v0` records later
without making that evidence schema responsible for running checks.

## Non-Goals

ASP-0005 tooling does not:

- Move ACES core SDL validators or redefine SDL semantics.
- Move capture or inventory workflow assets before the ownership issue resolves.
- Encode downstream catalog names, statuses, branch rules, labels, paths, or
  product runtime behavior into canonical pack checks.
- Require private repository state, credentials, network access, or hosted
  services for static validation.
- Replace the existing repository test suite as the completion gate.
