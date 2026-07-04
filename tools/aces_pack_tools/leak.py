"""Static leak / scrub scan for pack content.

The scanner reports secret-shaped material (private-key blocks, cloud access
keys, bearer tokens, assigned secrets) and any caller-supplied denylisted
vocabulary term. It ships no built-in vocabulary denylist: the terms a given
ecosystem must scrub are configuration, passed in by the caller, so this tool
stays reusable and carries no downstream-private vocabulary itself. Findings
report the pattern name, never the matched material.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from .model import Finding
from .schema import within_root

_SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    ("cloud-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Z0-9._\-]{20,}")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*['\"]?[A-Z0-9/+_\-]{12,}"
        ),
    ),
]

# Binary / non-text suffixes the scanner skips.
_SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".pdf", ".zip", ".gz", ".tar", ".tgz", ".pyc",
}


def scan_text(text: str, path: str, denylist_terms: tuple[str, ...] = ()) -> list[Finding]:
    """Scan one text blob for secret-shaped material and denylisted vocabulary."""
    findings: list[Finding] = []
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(Finding("leak", path, f"possible {name} material detected", family="secret"))
    lowered = text.lower()
    for term in denylist_terms:
        if term and term.lower() in lowered:
            # The term is caller-supplied private vocabulary; report the hit
            # without echoing the term back into the finding.
            findings.append(Finding("leak", path, "denylisted vocabulary term present", family="vocabulary"))
    return findings


def scan_pack(
    pack_root: str | Path,
    denylist_terms: tuple[str, ...] = (),
    skip_dirs: tuple[str, ...] = (".git",),
    extra_scanners: tuple[Callable[[str, str], list[Finding]], ...] = (),
) -> list[Finding]:
    """Recursively scan a pack directory, skipping binaries and symlink escapes.

    ``extra_scanners`` are additional per-file text scanners ``(text, rel) ->
    findings`` run in the same walk as the built-in secret/denylist scan, so a
    caller can layer extra checks without a second traversal (and without those
    checks being baked into this reusable, vocabulary-free scanner).
    """
    root = Path(pack_root).resolve()
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in skip_dirs for part in relative.parts):
            continue
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        rel = relative.as_posix()
        if not within_root(root, path):
            # A pack-supplied symlink resolving outside the pack root must not be
            # read: doing so would scan (and could leak) files beyond the boundary.
            findings.append(Finding("leak", rel, "path is a symlink escaping the pack root", family="path"))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings.extend(scan_text(text, rel, denylist_terms))
        for scanner in extra_scanners:
            findings.extend(scanner(text, rel))
    return findings
