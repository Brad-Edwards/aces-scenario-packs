"""Command-line entry point for the scenario-pack checks.

Ordinary CLI behavior: ``argparse`` usage, exit codes (0 clean, 1 findings,
2 usage/IO error), findings on stdout, diagnostics on stderr. No logging
framework, daemon, cache, or network dependency.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .leak import scan_pack, scan_text
from .release import check_release
from .schema import SchemaIndex
from .validate import validate_pack, validate_record

_DEFAULT_INDEX = "schemas/index.json"


def _read_denylist(path) -> tuple:
    if not path:
        return ()
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return tuple(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aces_pack_tools",
        description="Static, offline validation and release checks for ACES scenario packs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate pack records against published schemas.")
    validate.add_argument("target", help="A JSON record file (with --family) or a pack directory.")
    validate.add_argument("--family", help="Schema family when the target is a single record.")
    validate.add_argument("--schema-index", default=_DEFAULT_INDEX, help="Path to schemas/index.json.")
    validate.add_argument("--format", choices=("text", "json"), default="text")

    leak = sub.add_parser("leak", help="Scan pack content for secret-shaped or denylisted material.")
    leak.add_argument("target", help="A file or directory to scan.")
    leak.add_argument("--denylist", help="File of denylisted terms, one per line (# comments allowed).")
    leak.add_argument("--format", choices=("text", "json"), default="text")

    release = sub.add_parser("release", help="Validate a release record and cross-check schema versions.")
    release.add_argument("record", help="A release JSON record.")
    release.add_argument("--schema-index", default=_DEFAULT_INDEX, help="Path to schemas/index.json.")
    release.add_argument("--format", choices=("text", "json"), default="text")

    return parser


def _dispatch(args) -> list:
    if args.command == "validate":
        index = SchemaIndex(args.schema_index)
        target = Path(args.target)
        if args.family:
            return validate_record(target, args.family, index)
        if target.is_dir():
            return validate_pack(target, index)
        raise ValueError(
            "validate: a file target requires --family; a directory target validates the whole pack"
        )
    if args.command == "leak":
        target = Path(args.target)
        denylist = _read_denylist(args.denylist)
        if target.is_dir():
            return scan_pack(target, denylist_terms=denylist)
        return scan_text(target.read_text(encoding="utf-8"), target.name, denylist)
    if args.command == "release":
        return check_release(Path(args.record), SchemaIndex(args.schema_index))
    raise ValueError(f"unknown command: {args.command}")


def _emit(findings, fmt) -> None:
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    if fmt == "json":
        payload = {
            "findings": [f.to_dict() for f in findings],
            "summary": {"errors": errors, "warnings": warnings},
        }
        print(json.dumps(payload, indent=2))
    else:
        for finding in findings:
            print(finding.format_text())
        print(f"{errors} error(s), {warnings} warning(s)", file=sys.stderr)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        findings = _dispatch(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _emit(findings, args.format)
    return 1 if any(f.severity == "error" for f in findings) else 0
