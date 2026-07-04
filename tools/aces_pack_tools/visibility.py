"""Runtime-visibility tiers, participant leak scan, and packaging-boundary gates.

The runtime-visibility axis classifies each declared pack artifact root by who
may see it at runtime. It is orthogonal to the ``artifact-boundary`` disposition
axis (how an artifact enters the pack) and is enforced by two gates the schema
alone cannot express:

  * a leak scan of every participant-visible root for secret-shaped material and
    the generic *structural* indicators of operator/oracle content (answers,
    flags, credentials, proof predicates, scoring internals, hidden-path
    labels); and
  * a packaging boundary split that stages each tier into its own release root
    with path-containment checks, so operator/oracle/distribution-restricted
    material can never be copied into a participant artifact.

The structural indicator terms below are generic, ecosystem-independent
categories drawn from the incumbent pack convention — they are contract-level
semantics, not any downstream catalog's private vocabulary. Callers may extend
the scan with their own denylist terms; those are threaded through the shared
leak scanner. Findings report the category only, never the matched text.

Tier behavior lives in one declarative policy table (``_TIER_POLICY``) so a
future tier is a table row plus an enum value, not a validator rewrite.
"""

from __future__ import annotations

import re
from pathlib import Path
from collections.abc import Callable
from dataclasses import dataclass

from . import leak
from .model import Finding
from .schema import normalize_subtree, pack_relative, resolve_within_root, subtrees_overlap

# Canonical filename for a pack's runtime-visibility record.
RECORD_NAME = "runtime-visibility.json"

# The single source of truth for tier behavior. Each tier answers: is it
# participant-visible (and therefore leak-scanned), and which release root does
# it stage into during the packaging boundary split.
_TIER_POLICY: dict[str, dict[str, object]] = {
    "participant-visible": {"participant_visible": True, "release_root": "participant"},
    "operator-only": {"participant_visible": False, "release_root": "operator"},
    "oracle-only": {"participant_visible": False, "release_root": "oracle"},
    "distribution-restricted": {"participant_visible": False, "release_root": "restricted"},
}

TIERS: tuple[str, ...] = tuple(_TIER_POLICY)

# Generic structural indicators of operator/oracle content that must not appear
# in a participant-visible root. Word-boundary matching keeps "flag" from
# tripping on "flagship". These are contract categories, not private vocabulary;
# ecosystem-specific terms are supplied by the caller as a denylist.
_RESTRICTED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("flag", re.compile(r"(?i)\bflags?\b")),
    ("answer", re.compile(r"(?i)\banswers?\b")),
    ("solution", re.compile(r"(?i)\bsolutions?\b")),
    ("proof-predicate", re.compile(r"(?i)\bproof\b")),
    ("scoring-internal", re.compile(r"(?i)\bscoring\b|\brubric\b")),
    ("oracle", re.compile(r"(?i)\boracle\b")),
    ("credential", re.compile(r"(?i)\bcredentials?\b")),
    ("hidden-path", re.compile(r"(?i)\bhidden[ _-]?path\b")),
]


def tier_policy(tier: str) -> dict[str, object]:
    """Return the policy row for ``tier`` (participant_visible + release_root)."""
    if tier not in _TIER_POLICY:
        raise ValueError(f"unknown runtime-visibility tier: {tier}")
    # Return a copy so callers cannot mutate the shared policy table.
    return dict(_TIER_POLICY[tier])


def restricted_tier_findings(text: str, path: str) -> list[Finding]:
    """Report generic operator/oracle structural indicators found in ``text``.

    The finding names the indicator *category* (for example ``flag``); it never
    echoes the surrounding participant text, matched span, or credential-shaped
    material back into the output.
    """
    findings: list[Finding] = []
    for name, pattern in _RESTRICTED_PATTERNS:
        if pattern.search(text):
            findings.append(
                Finding(
                    "leak",
                    path,
                    f"restricted-tier indicator in participant-visible content: {name}",
                    family="restricted-tier",
                )
            )
    return findings


def _reroot(finding: Finding, prefix: str) -> Finding:
    """Return ``finding`` with its path re-based under the pack-relative ``prefix``."""
    if not prefix:
        return finding
    path = finding.path if finding.path in ("", "<pack>") else f"{prefix}/{finding.path}"
    return Finding(finding.check, path, finding.message, family=finding.family, severity=finding.severity)


def _scan_participant_target(target: Path, prefix: str, extra_terms: tuple[str, ...]) -> list[Finding]:
    """Leak-scan one existing participant target (file or directory), pack-relative."""
    scanners: tuple[Callable[[str, str], list[Finding]], ...] = (restricted_tier_findings,)
    if target.is_dir():
        # ``scan_pack`` handles binary skips, symlink escapes, and the walk; the
        # extra scanner adds the structural-indicator patterns in the same pass.
        return [
            _reroot(f, prefix)
            for f in leak.scan_pack(target, denylist_terms=extra_terms, extra_scanners=scanners)
        ]
    try:
        text = target.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    # A single-file root's own pack-relative path is ``prefix``; use it directly
    # (re-rooting would double it, e.g. ``brief.md/brief.md``).
    findings = leak.scan_text(text, prefix, extra_terms)
    findings.extend(restricted_tier_findings(text, prefix))
    return findings


def check_visibility(
    record: object,
    root: str | Path,
    rel: str,
    extra_terms: tuple[str, ...] = (),
) -> list[Finding]:
    """Validate a runtime-visibility record's boundary gates against a pack root.

    Gates: path containment for every declared root (reject ``..``, absolute
    paths, and symlink escapes), tier-conflict detection when one root is
    classified into two tiers, and a leak scan of every existing
    participant-visible root. Schema-shape errors are handled separately by the
    conformance checker; this covers what the schema cannot express.
    """
    if not isinstance(record, dict):
        return []
    pack_root = Path(root).resolve()
    plans, findings = staging_plan(record, pack_root, rel)
    findings.extend(_conflict_findings(record, rel))
    findings.extend(_participant_leak_findings(plans, pack_root, extra_terms))
    return findings


def _conflict_findings(record: dict[str, object], rel: str) -> list[Finding]:
    """Flag overlapping artifact roots that carry different runtime-visibility tiers.

    Two roots whose subtrees overlap (ancestor/descendant/equal) but carry
    different tiers would let the more-restricted subtree stage into, or be
    scanned as, the other tier. Rejecting them keeps recursive staging and
    scanning within a single tier.
    """
    classified: list[tuple[tuple[str, ...], str]] = []
    for item in record.get("roots", []) or []:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        visibility = item.get("visibility")
        if isinstance(path, str) and isinstance(visibility, str):
            classified.append((normalize_subtree(path), visibility))
    findings: list[Finding] = []
    for i, (left, left_tier) in enumerate(classified):
        for right, right_tier in classified[i + 1:]:
            if left_tier != right_tier and subtrees_overlap(left, right):
                findings.append(
                    Finding(
                        "runtime-visibility",
                        rel,
                        "overlapping artifact roots carry conflicting runtime-visibility tiers",
                        family="runtime-visibility",
                    )
                )
    return findings


def _participant_leak_findings(
    plans: list["StagePlan"], pack_root: Path, extra_terms: tuple[str, ...]
) -> list[Finding]:
    """Leak-scan every participant-visible root, warning when a declared root is missing."""
    findings: list[Finding] = []
    for plan in plans:
        if not tier_policy(plan.tier)["participant_visible"]:
            continue
        target = (pack_root / plan.source).resolve()
        if not target.exists():
            # A declared participant root absent from disk must not silently skip
            # the leak scan; surface it as a warning (mirrors artifact-boundary).
            findings.append(
                Finding(
                    "runtime-visibility",
                    plan.source,
                    "declared participant-visible root is missing from the pack",
                    family="runtime-visibility",
                    severity="warning",
                )
            )
            continue
        findings.extend(_scan_participant_target(target, plan.source, extra_terms))
    return findings


@dataclass(frozen=True)
class StagePlan(object):
    """One packaging-boundary staging entry: a source root and its tier release destination."""

    source: str
    dest: str
    tier: str


def staging_plan(
    record: object, root: str | Path, rel: str = RECORD_NAME
) -> tuple[list[StagePlan], list[Finding]]:
    """Compute the per-tier packaging boundary split for a runtime-visibility record.

    Each declared root is resolved within the pack root (rejecting ``..``,
    absolute paths, and symlink escapes) and mapped to its tier's own release
    root, so operator/oracle/distribution-restricted material can never target
    the participant release root. A root stages its whole subtree; the overlap
    gate in :func:`check_visibility` guarantees no different-tier root nests
    inside another, so recursive staging stays within one tier. Returns the
    staging plan and any containment findings; a root that fails containment is
    reported and omitted from the plan.
    """
    pack_root = Path(root).resolve()
    plans: list[StagePlan] = []
    findings: list[Finding] = []
    if not isinstance(record, dict):
        return plans, findings
    for item in record.get("roots", []) or []:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        visibility = item.get("visibility")
        if not isinstance(path, str) or visibility not in _TIER_POLICY:
            # Shape/enum errors are the conformance checker's job; skip here.
            continue
        try:
            target = resolve_within_root(pack_root, path.rstrip("/"))
        except ValueError as exc:
            findings.append(Finding("runtime-visibility", rel, str(exc), family="runtime-visibility"))
            continue
        source = pack_relative(pack_root, target)
        release_root = _TIER_POLICY[visibility]["release_root"]
        plans.append(StagePlan(source=source, dest=f"{release_root}/{source}", tier=visibility))
    return plans, findings
