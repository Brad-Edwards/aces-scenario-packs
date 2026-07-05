#!/usr/bin/env python3
"""Create a new scenario pack from the packaged template.

The script is intentionally small and conservative: it validates the pack id,
copies the packaged template into the consumer catalog's ``scenarios/<pack-id>/``,
patches obvious placeholders, and leaves the doctrine and golden-readiness
checklist in place for the author to work through.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import shutil
import sys
from pathlib import Path

PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
README_FILE = "README.md"
PACK_FILE = "pack.yaml"
COMPATIBILITY_FILE = "pack.compatibility.yaml"

# The template ships inside this installed package; the new pack is created in the
# consumer catalog's scenarios/ directory.
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "template")


def repo_root(start: str | None = None) -> str:
    """Repo root."""
    here = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(here, ".git")) and \
                os.path.isdir(os.path.join(here, "scenarios")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            raise SystemExit("could not find repo root containing .git and scenarios/")
        here = parent


def title_from_pack_id(pack_id: str) -> str:
    """Title from pack id."""
    return " ".join(part.capitalize() for part in pack_id.split("-"))


def validate_pack_id(pack_id: str) -> None:
    """Validate pack id."""
    if not PACK_ID_RE.fullmatch(pack_id):
        raise SystemExit(
            "pack id must be lowercase kebab-case, start/end with a letter or "
            "digit, and contain only a-z, 0-9, and '-'")


def ensure_inside(parent: str, child: str) -> None:
    """Ensure inside."""
    parent_abs = os.path.abspath(parent)
    child_abs = os.path.abspath(child)
    if os.path.commonpath([parent_abs, child_abs]) != parent_abs:
        raise SystemExit(f"target escapes expected parent: {child}")


def scenario_pack_target(scenarios_root: str, pack_id: str) -> str:
    """Scenario pack target."""
    validate_pack_id(pack_id)
    scenarios = Path(scenarios_root).resolve(strict=True)
    target = (scenarios / pack_id).resolve(strict=False)
    if target.parent != scenarios:
        raise SystemExit(f"target escapes scenarios root: {pack_id}")
    return str(target)


def checked_pack_root(pack_root: str) -> Path:
    """Checked pack root."""
    root = Path(pack_root).resolve(strict=True)
    validate_pack_id(root.name)
    return root


@contextlib.contextmanager
def pack_root_cwd(pack_root: str):
    """Pack root cwd."""
    root = checked_pack_root(pack_root)
    original = os.getcwd()
    os.chdir(root)
    try:
        yield
    finally:
        os.chdir(original)


def apply_replacements(body: str, replacements: dict[str, str]) -> str:
    """Apply replacements."""
    for old, new in replacements.items():
        body = body.replace(old, new)
    return body


def replace_readme_text(pack_root: str, replacements: dict[str, str]) -> None:
    """Replace readme text."""
    with pack_root_cwd(pack_root):
        with open(README_FILE, "r", encoding="utf-8") as fh:
            body = fh.read()
        with open(README_FILE, "w", encoding="utf-8") as fh:
            fh.write(apply_replacements(body, replacements))


def replace_pack_yaml_text(pack_root: str, replacements: dict[str, str]) -> None:
    """Replace pack yaml text."""
    with pack_root_cwd(pack_root):
        with open(PACK_FILE, "r", encoding="utf-8") as fh:
            body = fh.read()
        with open(PACK_FILE, "w", encoding="utf-8") as fh:
            fh.write(apply_replacements(body, replacements))


def replace_optional_file_text(pack_root: str, rel_path: str,
                               replacements: dict[str, str]) -> None:
    """Replace optional file text."""
    with pack_root_cwd(pack_root):
        if not os.path.isfile(rel_path):
            return
        with open(rel_path, "r", encoding="utf-8") as fh:
            body = fh.read()
        with open(rel_path, "w", encoding="utf-8") as fh:
            fh.write(apply_replacements(body, replacements))


def append_issue_provenance(pack_root: str, issue: int) -> None:
    """Append issue provenance."""
    with pack_root_cwd(pack_root):
        with open(README_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"\n## Provenance\n\nCreated from GitHub issue #{issue}.\n")


def scaffold_pack(repo: str, pack_id: str, title: str, description: str,
                  requirement: str | None, issue: int | None) -> str:
    """Scaffold pack."""
    scenarios = os.path.join(repo, "scenarios")
    template = _TEMPLATE_DIR
    target = scenario_pack_target(scenarios, pack_id)
    if not os.path.isdir(template):
        raise SystemExit("missing packaged template")
    if os.path.exists(target):
        raise SystemExit(f"target already exists: scenarios/{pack_id}")

    shutil.copytree(
        template,
        target,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))

    replacements = {
        "<name>": pack_id,
        "Human-readable title": title,
        "One line: what the scenario is and what the player does.": description,
    }
    replace_readme_text(target, replacements)
    replace_pack_yaml_text(target, replacements)
    replace_optional_file_text(target, COMPATIBILITY_FILE, replacements)

    if requirement:
        replace_pack_yaml_text(target, {
            "requirement: null": f"requirement: {requirement}",
        })
        replace_optional_file_text(target, COMPATIBILITY_FILE, {
            "requirement: null": f"requirement: {requirement}",
        })

    if issue is not None:
        append_issue_provenance(target, issue)

    return target


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse args."""
    parser = argparse.ArgumentParser(
        description="Create scenarios/<pack-id>/ from scenarios/_template.")
    parser.add_argument("pack_id", help="lowercase kebab-case scenario pack id")
    parser.add_argument("--title", help="human-readable title")
    parser.add_argument(
        "--description",
        default="One line: what the scenario is and what the player does.",
        help="one-line pack description for pack.yaml")
    parser.add_argument("--requirement", help="Ground Control requirement UID")
    parser.add_argument("--issue", type=int, help="GitHub issue number")
    parser.add_argument("--repo", help="repository root; defaults to auto-detect")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    args = parse_args(argv or sys.argv[1:])
    root = repo_root(args.repo)
    title = args.title or title_from_pack_id(args.pack_id)
    target = scaffold_pack(
        root, args.pack_id, title, args.description, args.requirement, args.issue)
    rel = os.path.relpath(target, root)
    print(f"created {rel}")
    print("next steps:")
    print(f"  - edit {rel}/pack.yaml")
    print(f"  - replace {rel}/README.md with scenario-specific prose")
    print(f"  - fill {rel}/sdl/ and {rel}/docs/")
    print(f"  - use {rel}/docs/golden-readiness-checklist.md for milestone planning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
