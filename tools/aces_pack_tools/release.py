"""Release-record validation and schema-version cross-check.

A release record is validated against the ``release`` schema family, then its
declared ``schemaVersions`` are cross-checked against the schema index: each
referenced family must exist and its pinned version must match the published
version. This is a static check only; it never mutates git tags, GitHub
releases, or remote state (that automation is deferred, per the tooling
guardrails).
"""

from __future__ import annotations

from pathlib import Path

from .model import Finding
from .schema import SchemaIndex, conformance_errors, load_json


def check_release(record_path, index: SchemaIndex, rel=None) -> list:
    schema = index.schema_for("release")
    record = load_json(record_path)
    where = rel or Path(record_path).name
    findings = [
        Finding("release", where, err, family="release")
        for err in conformance_errors(record, schema)
    ]
    if not isinstance(record, dict):
        return findings
    for item in record.get("schemaVersions", []) or []:
        if not isinstance(item, dict):
            continue
        family = item.get("family")
        version = item.get("version")
        if family is None:
            continue
        if family not in index.families():
            # ``family`` is an untrusted value from the pack's release record.
            findings.append(
                Finding("release", where, "release references an unknown schema family", family="release")
            )
            continue
        published = index.entry(family).version
        if version is not None and version != published:
            # ``family`` is now a known (index-resolved) family and safe to name;
            # the pinned ``version`` is untrusted pack input and is not echoed.
            findings.append(
                Finding(
                    "release",
                    where,
                    f"release pins {family} at a version that differs from the published version {published!r}",
                    family="release",
                )
            )
    return findings
