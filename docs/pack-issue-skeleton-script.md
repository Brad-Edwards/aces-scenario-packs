# Pack Issue Skeleton Script

Use `scripts/create_scenario_pack_issue_skeleton.py` at the start of a new
scenario-pack effort. It creates the standard top-level GitHub issues that a
pack-design agent can then edit, refine, and split into child issues.

The script defaults to dry-run mode:

```sh
python3 scripts/create_scenario_pack_issue_skeleton.py \
  --pack-id example-pack \
  --title "Example Pack" \
  --milestone-title "Scenario pack: Example Pack" \
  --source "Source label: https://example.invalid/source" \
  --focus "One sentence describing what the participant does."
```

Apply only after the dry-run output is correct:

```sh
python3 scripts/create_scenario_pack_issue_skeleton.py \
  --pack-id example-pack \
  --title "Example Pack" \
  --milestone-title "Scenario pack: Example Pack" \
  --create-milestone \
  --source "Source label: https://example.invalid/source" \
  --focus "One sentence describing what the participant does." \
  --apply
```

If the milestone already exists, pass its number:

```sh
python3 scripts/create_scenario_pack_issue_skeleton.py \
  --pack-id example-pack \
  --title "Example Pack" \
  --milestone-number 42 \
  --apply
```

The skeleton issues are:

- scenario contract and pack skeleton
- topology, assets, and reference-triangle design
- hidden path, oracle, and validation model
- flag, challenge, and reference CTFd layer
- delivery profile bundles
- golden live-infrastructure build
- automated live rehearsal
- final manual participant walkthrough
- final docs, status, evidence, and teardown reconciliation

Re-running the script skips existing skeleton issues by title so it does not
overwrite an agent's edits. Pass `--refresh-existing` only when you intentionally
want to reapply the current template body to existing skeleton issues.

Extra labels are applied only if they already exist in the repository:

```sh
python3 scripts/create_scenario_pack_issue_skeleton.py \
  --pack-id example-pack \
  --milestone-number 42 \
  --label scenario:example-pack
```

This script is a GitHub issue setup helper; it does not scaffold files and does
not run the full Ground Control `/implement` workflow. Use
`aces-new-pack` separately for the pack source skeleton.
