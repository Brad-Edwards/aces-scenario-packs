#!/usr/bin/env python3
"""Changelog-driven version tooling (ADR 0007).

The version is a pure function of the towncrier fragments in ``changelog.d/``:
the highest-severity fragment type accumulated since the last release decides
the bump. The changelog is therefore the SINGLE source of the version, so the
release tag and ``CHANGELOG.md`` can never drift.

Fragment type -> bump:
  * ``breaking`` / ``removed``             -> major
  * ``added`` / ``changed`` / ``deprecated`` -> minor
  * ``security`` / ``fixed``               -> patch

Pre-1.0 (``0.y.z``) follows SemVer's 0.x rule: a major-level change bumps the
minor, not the major.

Subcommands:
  next     Print the next version from ``changelog.d/`` fragments + the last
           tag. Exits 3 when there are no release-worthy fragments.
  current  Print the newest version documented in ``CHANGELOG.md`` (``## [X.Y.Z]``).
  notes    Print the body of that newest ``CHANGELOG.md`` section (release notes).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_FRAGMENTS = _REPO / "changelog.d"
_CHANGELOG = _REPO / "CHANGELOG.md"

#: Fragment type -> bump level (0 patch, 1 minor, 2 major).
BUMP_LEVEL: dict[str, int] = {
    "breaking": 2,
    "removed": 2,
    "added": 1,
    "changed": 1,
    "deprecated": 1,
    "security": 0,
    "fixed": 0,
}

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_SECTION = re.compile(r"^##\s*\[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def bump_level(types: Iterable[str]) -> int | None:
    """Return the highest bump level among ``types``, or ``None`` if none apply."""
    levels = [BUMP_LEVEL[t] for t in types if t in BUMP_LEVEL]
    return max(levels) if levels else None


def apply_bump(base: tuple[int, int, int], level: int) -> str:
    """Apply a bump level to ``base``, honouring the pre-1.0 (0.x) rule."""
    major, minor, patch = base
    # Pre-1.0: a breaking/major change bumps the minor, not the major.
    if major == 0 and level == 2:
        level = 1
    if level == 2:
        return f"{major + 1}.0.0"
    if level == 1:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def fragment_types(directory: Path = _FRAGMENTS) -> list[str]:
    """Collect the towncrier fragment types present in ``directory``."""
    types: list[str] = []
    if not directory.is_dir():
        return types
    for path in directory.glob("*.md"):
        if path.name == "README.md" or path.name.startswith("_"):
            continue
        # <issue>.<type>.md  or  +slug.<type>.md
        parts = path.name.split(".")
        if len(parts) >= 3:
            types.append(parts[-2])
    return types


def last_version() -> tuple[int, int, int]:
    """Return the newest ``vX.Y.Z`` git tag as a tuple, or ``(0, 0, 0)``."""
    try:
        out = subprocess.run(
            ["git", "tag", "--list", "v*.*.*"],
            cwd=_REPO, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return (0, 0, 0)
    versions = [
        tuple(int(x) for x in m.groups())
        for line in out.split()
        if (m := _SEMVER.match(line.lstrip("v")))
    ]
    return max(versions) if versions else (0, 0, 0)


def next_version() -> str | None:
    """Compute the next version from fragments + the last tag, or ``None``."""
    level = bump_level(fragment_types())
    if level is None:
        return None
    return apply_bump(last_version(), level)


def changelog_version(text: str | None = None) -> str | None:
    """Return the newest version documented in ``CHANGELOG.md``."""
    if text is None:
        if not _CHANGELOG.exists():
            return None
        text = _CHANGELOG.read_text(encoding="utf-8")
    m = _SECTION.search(text)
    return m.group(1) if m else None


def changelog_notes(text: str | None = None) -> str:
    """Return the body of the newest ``CHANGELOG.md`` section (release notes)."""
    if text is None:
        text = _CHANGELOG.read_text(encoding="utf-8") if _CHANGELOG.exists() else ""
    matches = list(_SECTION.finditer(text))
    if not matches:
        return ""
    # Start after the heading LINE (skip the "## [X.Y.Z] - date" line itself).
    line_end = text.find("\n", matches[0].start())
    start = line_end + 1 if line_end != -1 else matches[0].end()
    end = matches[1].start() if len(matches) > 1 else len(text)
    return text[start:end].strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Changelog-driven version tooling.")
    parser.add_argument("cmd", choices=("next", "current", "notes"))
    args = parser.parse_args(argv)

    if args.cmd == "next":
        version = next_version()
        if version is None:
            print("no release-worthy changelog fragments", file=sys.stderr)
            return 3
        print(version)
        return 0
    if args.cmd == "current":
        version = changelog_version()
        if version is None:
            print("no version section in CHANGELOG.md", file=sys.stderr)
            return 3
        print(version)
        return 0
    print(changelog_notes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
