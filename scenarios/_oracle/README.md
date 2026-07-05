# Shared Validation Oracle Model

`scenarios/_oracle/` is shared operator/oracle-only source. It is not a
scenario pack and is skipped by pack discovery. The repo-wide content CI runs it
through a dedicated gate instead:

```sh
python3 -m unittest discover -s scenarios/_oracle/tests
python3 scripts/ci/scenario_content_ci.py
```

The reusable model defines the common shape that ACES packs use when they
need hidden validation or scoring contracts:

- canonical, optional, and telemetry-only path steps;
- prerequisites, success states, failure states, and reset ownership;
- required and optional evidence with digest-safe proof fields;
- accepted alternates as explicit, reviewable award rows tied to the same
  outcome;
- consumer adapters for native scoring, CTFd, operator debriefs, and
  agent-benchmark exports.

The model is a source contract, not a runtime engine. Validators read committed
pack artifacts and digest-safe evidence references; they do not write scores,
create CTFd solves, mutate scenario state, trigger participant actions, or
consume one-time proof.

## Fixture Purpose

The fixtures under `fixtures/` are representative examples for model coverage.
They are not authoritative pack migrations and they do not replace the existing
APT29 or FIN7/Carbanak pack-local oracle validators. They prove that one shared
shape can express:

- APT29 success-state outcomes, optional side paths, native/CTFd consumers, and
  equivalence predicates.
- FIN7/Carbanak staged objective proof, synthetic data safety, contained exfil,
  optional capstone credit, and audited equivalence rows.
- Wizard Spider recoverable destructive-impact proof and blocking failure
  states such as irreversible wipe or missing decryptor proof.
- Scattered Spider deterministic identity/helpdesk workflow proof, state
  prerequisites, contained SaaS exfil, and participant-safe benchmark export.

## Visibility Rules

Oracle roots and participant roots must not overlap. Participant and
agent-benchmark exports may expose stable objective ids and award summaries, but
they must not expose hidden path joins, `S-*` states, predicates, raw proof,
answers, credentials, flags, or next-step hints. Operator debrief exports may
include hidden joins because they are operator-only.

Pack-local participant surfaces remain covered by
`scripts/ci/scenario_content_ci.py` leak scans. This shared directory can carry
operator tokens because it is never a participant-facing root.
