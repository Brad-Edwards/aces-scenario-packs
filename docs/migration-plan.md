# Migration Planning

Migration work must stay issue-driven. The initial issue set separates
repository standup from actual movement of content.

Each migration issue should state:

- Source repository and source paths.
- Target path in this repository.
- Scrub requirements for names, paths, labels, issue references, statuses, and
  private assumptions.
- Whether the migrated material becomes normative contract, guidance, example,
  or tooling.
- Required ACES-side and APTL-side reference updates.
- Validation commands and expected evidence.

Do not migrate material only because it exists elsewhere. Move it only when it
belongs to the public ACES scenario-pack contract or to reusable adoption
support for that contract.

Scrub requirements for migrated content and canonical docs are defined in the
[documentation scrub policy](scrub-policy.md); each migration issue carries a
source-specific scrub checklist derived from it, and keeps its source-specific
terms in a private, caller-supplied scanner denylist rather than in the issue.
