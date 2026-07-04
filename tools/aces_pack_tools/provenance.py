"""Provenance-ledger gates the schema alone cannot express (contract v1, #21).

The four-part provenance ledger — a ``sources[]`` ledger, per-artifact-root
distribution class, a content-safety attestation, and a publication-review
checklist — is shape-checked by the published ``provenance`` schema. The policy
that makes a ledger *releasable* is enforced here, mirroring the way
``visibility.py`` enforces the runtime-visibility gates the schema cannot state:

  * **content-safety all-true** — every named attestation gate must be true; the
    policy is exclusion of real sensitive content, never a weaker class;
  * **publication-review** — any ``blocked`` gate fails validation (kept distinct
    from a content-safety failure: review status is clearance to publish, not
    whether the content is safe);
  * **attribution completeness** — a source that requires attribution must carry
    non-empty attribution text;
  * **source-reference integrity** — every artifact-root source reference must
    resolve to a declared source id;
  * **artifact-root containment** — every artifact root (base *and* overlay)
    resolves under the pack root on its raw path, rejecting absolute paths, ``..``
    traversal, and symlink escapes before the distribution class is trusted; and
  * **overlay non-overlap** — every ``consumer-specific`` artifact root never
    overlaps a base artifact root, so removing an overlay removes its claims
    without touching the base pack.

Findings name the failing gate category only. They never echo source ids,
attribution text, license text, or any other untrusted ledger content, per the
tooling error-envelope guardrail.

The gate sets are declarative tuples so a future attestation gate, review gate,
or distribution class is a table entry plus a fixture, not a validator rewrite.
"""

from __future__ import annotations

from pathlib import Path

from .model import Finding
from .schema import normalize_subtree, resolve_within_root, subtrees_overlap

# Canonical filename for a pack's provenance record.
RECORD_NAME = "provenance.json"

# Named content-safety attestation gates; every one must be true for release.
CONTENT_SAFETY_GATES: tuple[str, ...] = (
    "noRealMalware",
    "noRealThirdPartyTargets",
    "noRealCredentials",
    "noSensitiveData",
    "offensiveToolingBoundary",
)

# Named publication-review gates; a "blocked" status on any of them fails.
PUBLICATION_REVIEW_GATES: tuple[str, ...] = (
    "licensing",
    "attribution",
    "sensitiveData",
    "offensiveTooling",
    "consumerOverlay",
)

# The distribution class that marks a removable consumer overlay root.
OVERLAY_CLASS = "consumer-specific"


def _content_safety_findings(record: dict[str, object], rel: str) -> list[Finding]:
    """Flag any named content-safety attestation gate that is not exactly true."""
    attestation = record.get("contentSafety")
    if not isinstance(attestation, dict):
        return []
    findings: list[Finding] = []
    for gate in CONTENT_SAFETY_GATES:
        if attestation.get(gate) is not True:
            findings.append(
                Finding(
                    "provenance",
                    rel,
                    f"content-safety attestation gate not satisfied: {gate}",
                    family="content-safety",
                )
            )
    return findings


def _publication_review_findings(record: dict[str, object], rel: str) -> list[Finding]:
    """Flag any publication-review gate whose status is blocked."""
    review = record.get("publicationReview")
    if not isinstance(review, dict):
        return []
    findings: list[Finding] = []
    for gate in PUBLICATION_REVIEW_GATES:
        if review.get(gate) == "blocked":
            findings.append(
                Finding(
                    "provenance",
                    rel,
                    f"publication-review gate is blocked: {gate}",
                    family="publication-review",
                )
            )
    return findings


def _attribution_findings(record: dict[str, object], rel: str) -> list[Finding]:
    """Flag sources that require attribution but carry no non-empty attribution text."""
    findings: list[Finding] = []
    for source in record.get("sources", []) or []:
        if not isinstance(source, dict) or source.get("attributionRequired") is not True:
            continue
        text = source.get("attributionText")
        if not isinstance(text, str) or not text.strip():
            # The source id is untrusted ledger input; do not echo it.
            findings.append(
                Finding(
                    "provenance",
                    rel,
                    "source requires attribution but has no attribution text",
                    family="attribution",
                )
            )
    return findings


def _source_reference_findings(record: dict[str, object], rel: str) -> list[Finding]:
    """Flag artifact-root source references that do not resolve to a declared source id."""
    declared = {
        source["id"]
        for source in record.get("sources", []) or []
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }
    findings: list[Finding] = []
    for artifact in record.get("artifacts", []) or []:
        if not isinstance(artifact, dict):
            continue
        for ref in artifact.get("sources", []) or []:
            if ref not in declared:
                # The reference is untrusted ledger input; report the category only.
                findings.append(
                    Finding(
                        "provenance",
                        rel,
                        "artifact references a source id that is not declared in sources",
                        family="source-reference",
                    )
                )
    return findings


def _artifact_root_findings(record: dict[str, object], root: Path, rel: str) -> list[Finding]:
    """Flag artifact roots that escape the pack, and overlays that overlap a base root.

    Every ``artifacts[].path`` — base *and* consumer-specific overlay — is a
    security-relevant local path that downstream packaging or publication tooling
    trusts once ``validate`` accepts the record. So each raw path is checked for
    containment *before* any normalization or distribution-class classification:
    absolute paths, ``..`` traversal, and symlink escapes are rejected on the
    value as written (never ``rstrip``-ed, so a bare ``/`` cannot collapse to the
    pack root and slip through). A path is classified into a base or overlay root
    only after it is proven contained.

    A consumer overlay must additionally be removable without touching the base
    pack, so it must not share a subtree with any base (non-consumer-specific)
    artifact root.
    """
    base_roots, overlay_parts_list, findings = _classify_artifact_roots(record, root, rel)
    findings.extend(_overlay_overlap_findings(base_roots, overlay_parts_list, rel))
    return findings


def _classify_artifact_roots(
    record: dict[str, object], root: Path, rel: str
) -> tuple[list[tuple[str, ...]], list[tuple[str, ...]], list[Finding]]:
    """Containment-check every artifact root and split it into base vs overlay parts.

    Each raw ``artifacts[].path`` is validated for containment *before* any
    normalization or distribution-class classification, so an absolute or ``..``
    root cannot be canonicalized into innocuous parts and trusted outside the pack
    boundary. Returns the contained base roots, the contained overlay roots, and
    any containment findings.
    """
    base_roots: list[tuple[str, ...]] = []
    overlay_parts_list: list[tuple[str, ...]] = []
    findings: list[Finding] = []
    for artifact in record.get("artifacts", []) or []:
        if not isinstance(artifact, dict):
            continue
        path = artifact.get("path")
        if not isinstance(path, str):
            continue
        try:
            resolve_within_root(root, path)
        except ValueError as exc:
            findings.append(Finding("provenance", rel, str(exc), family="artifact-path"))
            continue
        parts = normalize_subtree(path)
        if artifact.get("distributionClass") == OVERLAY_CLASS:
            overlay_parts_list.append(parts)
        else:
            base_roots.append(parts)
    return base_roots, overlay_parts_list, findings


def _overlay_overlap_findings(
    base_roots: list[tuple[str, ...]],
    overlay_parts_list: list[tuple[str, ...]],
    rel: str,
) -> list[Finding]:
    """Flag consumer overlay roots that share a subtree with any base artifact root."""
    findings: list[Finding] = []
    for overlay_parts in overlay_parts_list:
        if any(subtrees_overlap(overlay_parts, base) for base in base_roots):
            findings.append(
                Finding(
                    "provenance",
                    rel,
                    "consumer-specific overlay root overlaps a base artifact root",
                    family="overlay",
                )
            )
    return findings


def check_provenance(record: object, root: str | Path, rel: str = RECORD_NAME) -> list[Finding]:
    """Validate a provenance record's contract gates against a pack root.

    Gates: content-safety all-true, publication-review blocked-status rejection,
    attribution completeness, source-reference integrity, and consumer-overlay
    path containment / non-overlap. Schema-shape errors (missing parts, unknown
    enum values, wrong types) are the conformance checker's job and are handled
    separately; this covers what the schema cannot express.
    """
    if not isinstance(record, dict):
        return []
    pack_root = Path(root).resolve()
    findings: list[Finding] = []
    findings.extend(_content_safety_findings(record, rel))
    findings.extend(_publication_review_findings(record, rel))
    findings.extend(_attribution_findings(record, rel))
    findings.extend(_source_reference_findings(record, rel))
    findings.extend(_artifact_root_findings(record, pack_root, rel))
    return findings
