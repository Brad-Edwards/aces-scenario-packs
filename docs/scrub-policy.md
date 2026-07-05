# Documentation Scrub Policy

Canonical scenario-pack docs and any content migrated into this repository must
be adoptable without downstream catalog context or branding. This policy defines
what must be scrubbed, how to scrub it, and how the repository enforces the
scrub.

It consolidates the scrub obligations already referenced in the
[repository charter](repository-charter.md), the
[migration plan](migration-plan.md), the
[tooling design guardrails](tooling-design-guardrails.md) (scrub/leak gate),
[`SECURITY.md`](../SECURITY.md), and the pull-request boundary checklist.

## Scope

- **Canonical docs**: everything under `docs/`, `contracts/`, `schemas/`
  narrative, `templates/`, `examples/`, and the top-level `README`,
  `CONTRIBUTING`, `SECURITY`, and `SUPPORT` files.
- **Migrated content**: any material moved or adapted from another repository
  into this one.

ACES SDL semantics owned by ACES core are out of scope here; this policy governs
scenario-pack structure, guidance, templates, and examples.

## Scrub Targets

The following categories must be removed, or replaced with neutral,
ACES-native, publicly-adoptable equivalents, before content lands on a canonical
surface:

- Downstream catalog names, product names, and internal branding.
- Private repository paths and internal directory layouts.
- Private labels, milestones, and status vocabulary.
- Issue and pull-request numbers that reference private or unrelated trackers.
  (Public cross-links between the ACES-family repositories are allowed when they
  are planning references, not private state.)
- Branch rules and private workflow conventions.
- Product assumptions and customer-specific behavior.
- Private deployment details: internal hostnames, IP addresses, environment
  names, and infrastructure identifiers.
- Any other private reference that ties the content to a non-public deployment.

## Remove Or Replace

- Prefer **removal** when the private reference is incidental.
- Prefer **replacement with a neutral placeholder** when the content needs an
  example: use ACES-native, obviously-synthetic values (for example,
  `example-pack`, `acme-internal-catalog` as a stand-in denylist term in tests)
  and mark placeholder content as placeholder content.
- Never introduce a real private term into a canonical doc "as an example" — a
  documented category is enough; the term itself belongs in caller-supplied
  configuration, not in this repository.

## Enforcement

Two automated surfaces and two review gates enforce this policy.

### Automated

1. **Repository scrub sentinel** — the repository test suite scans every
   canonical file for a maintained set of highest-risk downstream catalog terms
   and fails if any appears (see `tests/test_repository_contract.py`). The
   maintained denylist lives only inside that excluded test module so the terms
   never leak onto a canonical surface, and a failure reports only the offending
   **file path**, never the matched term. Extend coverage by adding to that
   maintained list.
2. **Reusable leak/scrub scanner** — `aces_pack_tools` ships a `leak` command
   (`tools/aces_pack_tools/leak.py`) that scans a pack for secret-shaped
   material and for **caller-supplied** denylisted vocabulary
   (`leak --denylist <file>`). It ships no built-in vocabulary so the tool stays
   reusable and carries no private vocabulary itself; adopters and migration
   authors supply the denylist for their own source ecosystem, ideally in CI.
   Findings report the pattern or category name, never the matched material.

Packs additionally attest their scrub state through the `scrubStatus` field of
the [`provenance.v0`](../schemas/provenance.v0.schema.json) schema.

### Review

3. **Pull-request boundary checklist** — every PR confirms it "avoids downstream
   catalog vocabulary in canonical docs" (see the PR template).
4. **Migration scrub checklist** — every migration issue carries a
   source-specific scrub checklist (see the
   [migration task template](../.github/ISSUE_TEMPLATE/migration_task.md) and the
   [migration plan](migration-plan.md)) so the person moving content confirms
   each scrub category and runs the scanner against the source-specific denylist.

## Maintaining The Highest-Risk Vocabulary

The maintained sentinel denylist is the seam for repository-wide coverage; the
`leak --denylist` input is the seam for pack- and source-specific coverage. When
a new downstream term becomes high-risk, add it to the maintained sentinel list
(which lives only inside the excluded test module, never in a canonical doc) and,
for source-specific migrations, to the private, caller-supplied denylist file
that migration's scan reads. Never record the terms themselves in a migration
issue, pull request, or any other canonical surface — those surfaces reference
the private denylist and confirm the scan ran; they do not enumerate the terms.
