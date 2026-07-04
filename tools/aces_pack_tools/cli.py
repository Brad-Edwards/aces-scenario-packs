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
from .model import Finding
from .release import check_release
from .schema import SchemaIndex, _validated_file, conformance_errors, load_json, within_root
from .validate import validate_pack, validate_record
from .visibility import RECORD_NAME, check_visibility

_DEFAULT_INDEX = "schemas/index.json"
_INDEX_HELP = "Path to schemas/index.json."


def _read_denylist(path: str | None) -> tuple[str, ...]:
    """Read a denylist file (one term per line, ``#`` comments) into a tuple of terms."""
    if not path:
        return ()
    lines = _validated_file(path).read_text(encoding="utf-8").splitlines()
    return tuple(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the validate/leak/release subcommands."""
    parser = argparse.ArgumentParser(
        prog="aces_pack_tools",
        description="Static, offline validation and release checks for ACES scenario packs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate pack records against published schemas.")
    validate.add_argument("target", help="A JSON record file (with --family) or a pack directory.")
    validate.add_argument("--family", help="Schema family when the target is a single record.")
    validate.add_argument("--schema-index", default=_DEFAULT_INDEX, help=_INDEX_HELP)
    validate.add_argument("--format", choices=("text", "json"), default="text")

    leak = sub.add_parser("leak", help="Scan pack content for secret-shaped or denylisted material.")
    leak.add_argument("target", help="A file or directory to scan.")
    leak.add_argument("--denylist", help="File of denylisted terms, one per line (# comments allowed).")
    leak.add_argument("--format", choices=("text", "json"), default="text")

    release = sub.add_parser("release", help="Validate a release record and cross-check schema versions.")
    release.add_argument("record", help="A release JSON record.")
    release.add_argument("--schema-index", default=_DEFAULT_INDEX, help=_INDEX_HELP)
    release.add_argument("--format", choices=("text", "json"), default="text")

    visibility = sub.add_parser(
        "visibility",
        help="Check a pack's runtime-visibility record: tier containment and participant leak scan.",
    )
    visibility.add_argument("target", help="A pack directory containing runtime-visibility.json.")
    visibility.add_argument("--denylist", help="File of operator/oracle leak terms, one per line (# comments allowed).")
    visibility.add_argument("--schema-index", default=_DEFAULT_INDEX, help=_INDEX_HELP)
    visibility.add_argument("--format", choices=("text", "json"), default="text")

    return parser


def _run_validate(args: argparse.Namespace) -> list[Finding]:
    """Handle the ``validate`` subcommand: a single record (--family) or a whole pack."""
    index = SchemaIndex(args.schema_index)
    target = Path(args.target)
    if args.family:
        return validate_record(target, args.family, index)
    if target.is_dir():
        return validate_pack(target, index)
    raise ValueError(
        "validate: a file target requires --family; a directory target validates the whole pack"
    )


def _run_leak(args: argparse.Namespace) -> list[Finding]:
    """Handle the ``leak`` subcommand: scan a directory or a single validated file."""
    target = Path(args.target)
    denylist = _read_denylist(args.denylist)
    if target.is_dir():
        return scan_pack(target, denylist_terms=denylist)
    validated = _validated_file(args.target)
    return scan_text(validated.read_text(encoding="utf-8"), target.name, denylist)


def _run_release(args: argparse.Namespace) -> list[Finding]:
    """Handle the ``release`` subcommand: validate a release record."""
    return check_release(Path(args.record), SchemaIndex(args.schema_index))


def _run_visibility(args: argparse.Namespace) -> list[Finding]:
    """Handle the ``visibility`` subcommand: runtime-visibility record + boundary gates.

    Validates the pack's ``runtime-visibility.json`` against its schema and runs
    the containment, tier-conflict, and participant leak gates. This is the
    release/CI entry point that re-runs the participant scan with a caller-supplied
    operator/oracle denylist. A pack with no visibility record has nothing to
    check and is clean.
    """
    index = SchemaIndex(args.schema_index)
    target = Path(args.target)
    if not target.is_dir():
        raise ValueError("visibility: target must be a pack directory")
    record_path = target / RECORD_NAME
    if not record_path.is_file():
        return []
    if not within_root(target, record_path):
        return [Finding("runtime-visibility", RECORD_NAME,
                        "record is a symlink escaping the pack root", family="runtime-visibility")]
    denylist = _read_denylist(args.denylist)
    record = load_json(record_path)
    schema = index.schema_for("runtime-visibility")
    findings = [
        Finding("schema", RECORD_NAME, err, family="runtime-visibility")
        for err in conformance_errors(record, schema)
    ]
    findings.extend(check_visibility(record, target, RECORD_NAME, extra_terms=denylist))
    return findings


_COMMANDS = {
    "validate": _run_validate,
    "leak": _run_leak,
    "release": _run_release,
    "visibility": _run_visibility,
}


def _dispatch(args: argparse.Namespace) -> list[Finding]:
    """Route parsed CLI ``args`` to the handler for the selected subcommand."""
    handler = _COMMANDS.get(args.command)
    if handler is None:
        raise ValueError(f"unknown command: {args.command}")
    return handler(args)


def _emit(findings: list[Finding], fmt: str) -> None:
    """Print findings (text or JSON) and a summary count line to stderr."""
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


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv``, run the selected check, print findings, and return an exit code."""
    args = build_parser().parse_args(argv)
    try:
        findings = _dispatch(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _emit(findings, args.format)
    return 1 if any(f.severity == "error" for f in findings) else 0
