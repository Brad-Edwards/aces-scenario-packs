"""Record, pack, and runtime-profile validation.

Validation is schema-driven: a record is checked against its published schema
family resolved through the schema index, plus a small set of contract gates the
schema alone cannot express (runtime-profile portability, artifact-boundary path
containment, cross-record packId consistency).
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import Finding
from .schema import (
    SchemaIndex,
    conformance_errors,
    load_json,
    pack_relative,
    resolve_within_root,
    within_root,
)
from .visibility import check_visibility

# A runtime profile's requirements must name portable capabilities, not private
# hosts, endpoints, IP literals, or product runtimes.
_PRIVATE_HOST = re.compile(
    r"https?://|://|@|\b\d{1,3}(?:\.\d{1,3}){3}\b|\.(?:internal|local|corp|lan|intranet)\b",
    re.IGNORECASE,
)

# Minimum pack shape (contracts/scenario-pack-contract.md, "Minimum Pack Shape"):
# identity/metadata, the SDL-contract/compatibility declaration, provenance, and
# lifecycle are required of every pack. SDL scenario definitions are ACES-core
# owned and are not validated here; optional layers are validated only when
# present. This is contract membership, not schema data, so it is a small
# declarative table rather than a field in schemas/index.json.
REQUIRED_FAMILIES = ("pack-metadata", "compatibility", "provenance", "lifecycle")


def _validate_loaded(record: object, family: str, index: SchemaIndex, rel: str) -> list[Finding]:
    """Validate an already-loaded ``record`` against schema ``family`` and profile gates."""
    # ``schema_for`` raises ValueError on an unknown family.
    schema = index.schema_for(family)
    findings = [
        Finding("schema", rel, err, family=family)
        for err in conformance_errors(record, schema)
    ]
    if family == "runtime-profile":
        findings.extend(check_profile(record, rel))
    return findings


def validate_record(
    record_path: str | Path, family: str, index: SchemaIndex, rel: str | None = None
) -> list[Finding]:
    """Validate a single JSON record file against its schema ``family``."""
    # Fail fast on an unknown family before reading the file.
    index.entry(family)
    record = load_json(record_path)
    return _validate_loaded(record, family, index, rel or Path(record_path).name)


def check_profile(record: object, path: str) -> list[Finding]:
    """Flag runtime-profile requirements that name a private host, endpoint, or IP."""
    findings: list[Finding] = []
    profile = record.get("profile") if isinstance(record, dict) else None
    if not isinstance(profile, dict):
        return findings
    for requirement in profile.get("requires", []) or []:
        if isinstance(requirement, str) and _PRIVATE_HOST.search(requirement):
            findings.append(
                Finding(
                    "profile",
                    path,
                    "runtime requirement is not portable (looks like a private host/endpoint)",
                    family="runtime-profile",
                )
            )
    return findings


def _check_artifact_boundary(record: object, root: Path, rel: str) -> list[Finding]:
    """Flag artifacts whose path escapes the pack root or is declared but missing."""
    findings: list[Finding] = []
    if not isinstance(record, dict):
        return findings
    for artifact in record.get("artifacts", []) or []:
        if not isinstance(artifact, dict):
            continue
        declared_path = artifact.get("path")
        disposition = artifact.get("disposition")
        if not isinstance(declared_path, str):
            continue
        try:
            target = resolve_within_root(root, declared_path.rstrip("/"))
        except ValueError as exc:
            findings.append(Finding("artifact-boundary", rel, str(exc), family="artifact-boundary"))
            continue
        if disposition in ("authored", "included") and not target.exists():
            findings.append(
                Finding(
                    "artifact-boundary",
                    pack_relative(root, target),
                    "declared artifact is missing from the pack",
                    family="artifact-boundary",
                    severity="warning",
                )
            )
    return findings


def validate_pack(pack_root: str | Path, index: SchemaIndex) -> list[Finding]:
    """Validate a pack directory against the published schemas and minimum shape.

    Records are discovered by the tool's own convention: a top-level
    ``<family>.json`` file per schema family. Every present record is validated;
    the minimum-shape records in ``REQUIRED_FAMILIES`` are additionally required
    (an absent one is an error, per the scenario-pack contract), while optional
    layers are validated only when present. A ``<family>.json`` that is a symlink
    resolving outside the pack root is refused rather than read: pack roots are
    untrusted, so a symlink must not pull a record from outside the boundary.
    """
    root = Path(pack_root).resolve()
    findings: list[Finding] = []
    pack_ids: dict[str, list[str]] = {}
    present: set[str] = set()
    for family in sorted(index.families()):
        record_path = root / f"{family}.json"
        if not record_path.is_file():
            continue
        if not within_root(root, record_path):
            findings.append(
                Finding("pack", f"{family}.json", "record is a symlink escaping the pack root", family=family)
            )
            continue
        present.add(family)
        rel = pack_relative(root, record_path)
        record = load_json(record_path)
        findings.extend(_validate_loaded(record, family, index, rel))
        if isinstance(record, dict) and isinstance(record.get("packId"), str):
            pack_ids.setdefault(record["packId"], []).append(rel)
        if family == "artifact-boundary":
            findings.extend(_check_artifact_boundary(record, root, rel))
        if family == "runtime-visibility":
            # The runtime-visibility axis adds path-containment, tier-conflict,
            # and participant-tier leak gates the schema alone cannot express.
            findings.extend(check_visibility(record, root, rel))
    for family in REQUIRED_FAMILIES:
        if family not in present:
            findings.append(
                Finding("pack", "<pack>", f"required record is missing: {family}.json", family=family)
            )
    if len(pack_ids) > 1:
        findings.append(
            Finding("packid", "<pack>", f"inconsistent packId across {len(pack_ids)} records")
        )
    return findings
