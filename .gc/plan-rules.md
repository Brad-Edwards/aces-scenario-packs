# aces-scenario-packs plan rules

Mandatory constraints for implementation plans in this repository.

- Plans MUST run `python3 -m unittest discover -s tests` before declaring
  completion.
- Plans MUST run `python3 -m compileall tests` before declaring completion.
- Plans MUST keep `.ground-control.yaml`, `.mcp.json`, and this file aligned
  when changing Ground Control support.
- Plans MUST keep IMPLEMENTS, TESTS, and DOCUMENTS traceability in Ground
  Control aligned with changed files and GitHub issues when a requirement is in
  scope.
- Plans MUST NOT move ACES core schemas, authoring tools, capture workflows, or
  example packs into this repository without a linked migration issue.
- Plans MUST NOT add downstream catalog names, paths, product assumptions,
  branch rules, labels, or private deployment vocabulary to canonical docs.
- Plans that add or change a published scenario-pack schema MUST also update the
  schema index and include a test or validation fixture that proves the schema is
  loadable.
- Plans that add or change a template pack MUST keep it self-contained and
  explicitly mark placeholder content as placeholder content.
