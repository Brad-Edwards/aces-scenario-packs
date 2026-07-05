#!/usr/bin/env python3
"""Cut a release: next version from pending towncrier fragments -> write
__version__ -> towncrier build. No git ops; commit on a release/vX.Y.Z branch
and open a PR to main."""
from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "src" / "aces_scenario_packs" / "__init__.py"   # {{VERSION_FILE}}
FRAGMENTS = ROOT / "changelog.d"
_V = re.compile(r'^__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', re.M)
MINOR = {"added", "changed", "deprecated"}; PATCH = {"fixed", "security"}
BREAK = {"removed", "breaking"}   # major (>=1.0); capped to minor pre-1.0


def cur():
    m = _V.search(INIT.read_text())
    if not m:
        sys.exit(f"no __version__ in {INIT}")
    return tuple(int(x) for x in m.groups())


def types():
    t = set()
    for f in FRAGMENTS.glob("*.md"):
        if f.name.startswith("_"):
            continue
        p = f.name.split(".")
        if len(p) >= 3:
            t.add(p[-2])
    return t


def nxt(c, t):
    M, m, p = c
    if t & BREAK:
        return f"{M + 1}.0.0" if M >= 1 else f"{M}.{m + 1}.0"
    if t & MINOR:
        return f"{M}.{m + 1}.0"
    if t & PATCH:
        return f"{M}.{m}.{p + 1}"
    return None


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--version")
    ns = a.parse_args()
    t = types()
    v = ns.version or (nxt(cur(), t) if t else sys.exit("no fragments; nothing to release"))
    if not v:
        sys.exit(f"fragment types {sorted(t)} imply no release")
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        sys.exit(f"bad version {v}")
    INIT.write_text(_V.sub(f'__version__ = "{v}"', INIT.read_text(), count=1))
    subprocess.run([sys.executable, "-m", "towncrier", "build", "--yes", "--version", v], cwd=ROOT, check=True)
    print(
        f"\nv{v} prepared. git switch -c release/v{v} && "
        f"git commit -am 'chore: release v{v}' && "
        f"gh pr create --base main --title 'chore: release v{v}' --fill"
    )


if __name__ == "__main__":
    raise SystemExit(main())
