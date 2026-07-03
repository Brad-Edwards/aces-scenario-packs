"""Schema-index loading, path safety, and a stdlib JSON Schema conformance checker.

The conformance checker covers exactly the JSON Schema keyword subset the
published scenario-pack schemas use. ``SUPPORTED_KEYWORDS`` together with
``collect_keywords`` lets callers guard against a schema introducing a keyword
the checker does not handle (see ``tests/test_pack_schema_index.py``); it is not
a general JSON Schema engine. This is the single source of truth for that
checker: the test suite imports it here rather than forking a second copy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"

# JSON Schema keywords the conformance checker understands. A published schema
# using a keyword absent here is a coverage gap the caller's coverage guard
# should flag rather than silently pass.
SUPPORTED_KEYWORDS = {
    "$schema",
    "$id",
    "$comment",
    "title",
    "description",
    "version",
    "type",
    "enum",
    "const",
    "required",
    "properties",
    "items",
    "minItems",
    "additionalProperties",
    "examples",
}

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "number": (int, float),
    "integer": int,
    "null": type(None),
}


def load_json(path) -> Any:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def type_matches(value, declared) -> bool:
    types = declared if isinstance(declared, list) else [declared]
    for name in types:
        py = _JSON_TYPES.get(name)
        if py is None:
            return True  # unknown type name; leave to the keyword-coverage guard
        # bool is a subclass of int in Python; keep the JSON distinction.
        if name in ("number", "integer") and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def redact_type(value) -> str:
    """Return the JSON type name of an untrusted value for safe finding text.

    Conformance failures locate the offending field (``where``) and state the
    schema-derived expectation, but must never echo the instance *value*: an
    untrusted pack record can carry a credential-shaped scalar, a private
    endpoint, or customer vocabulary that would then be reflected into public
    validation output. The JSON type name carries enough signal to act on
    without disclosing content.
    """
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return "value"


def conformance_errors(instance, schema, where="<root>") -> list:
    """Return human-readable conformance errors for ``instance`` against ``schema``.

    Recursive over the keyword subset in ``SUPPORTED_KEYWORDS``. Messages carry
    only the field location and the schema-derived expectation (const/enum/type,
    which come from the trusted schema, not the pack); the untrusted instance
    value is reduced to its JSON type via ``redact_type`` and never echoed.
    """
    errors: list = []

    if "const" in schema and instance != schema["const"]:
        errors.append(
            f"{where}: value ({redact_type(instance)}) does not match required const {schema['const']!r}"
        )

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{where}: value ({redact_type(instance)}) not in enum {schema['enum']!r}")

    declared = schema.get("type")
    if declared is not None and not type_matches(instance, declared):
        errors.append(f"{where}: expected type {declared!r}, got {redact_type(instance)}")
        return errors  # further keyword checks assume the declared shape

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{where}: missing required property {key!r}")
        props = schema.get("properties", {})
        for key, subschema in props.items():
            if key in instance:
                errors.extend(conformance_errors(instance[key], subschema, f"{where}.{key}"))
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(props))
            if extra:
                # Report the count only; the extra keys are untrusted pack input.
                noun = "property" if len(extra) == 1 else "properties"
                errors.append(f"{where}: {len(extra)} unexpected {noun}")

    if isinstance(instance, list):
        item_schema = schema.get("items")
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(
                f"{where}: has {len(instance)} items, fewer than minItems {schema['minItems']}"
            )
        if isinstance(item_schema, dict):
            for idx, item in enumerate(instance):
                errors.extend(conformance_errors(item, item_schema, f"{where}[{idx}]"))

    return errors


def collect_keywords(schema, seen: set) -> None:
    if isinstance(schema, dict):
        for key, value in schema.items():
            seen.add(key)
            if key == "properties" and isinstance(value, dict):
                for sub in value.values():
                    collect_keywords(sub, seen)
            elif key == "items":
                collect_keywords(value, seen)
            elif isinstance(value, dict):
                collect_keywords(value, seen)


def resolve_within_root(root, candidate) -> Path:
    """Resolve ``candidate`` under ``root``, rejecting traversal or symlink escape.

    ``Path.resolve()`` normalizes ``..`` and follows symlinks, so a candidate
    that lands outside the resolved root — via ``../`` or a symlink — raises
    ``ValueError``. Pack roots are treated as untrusted input.
    """
    root = Path(root).resolve()
    target = (root / candidate).resolve()
    if target != root and root not in target.parents:
        # The candidate is untrusted pack input; do not echo it back.
        raise ValueError("path escapes pack root")
    return target


def within_root(root, path) -> bool:
    """True when ``path`` resolves to a location inside ``root`` (symlink-safe).

    ``Path.resolve()`` follows symlinks, so a file whose lexical location is
    under ``root`` but whose target escapes it returns ``False``. Directory
    walkers use this to refuse reading pack-supplied symlinks that point outside
    the untrusted pack boundary.
    """
    root = Path(root).resolve()
    target = Path(path).resolve()
    return target == root or root in target.parents


def pack_relative(root, path) -> str:
    root = Path(root).resolve()
    path = Path(path).resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


@dataclass(frozen=True)
class SchemaEntry:
    family: str
    id: str
    path: str
    version: str
    status: str
    fixtures: tuple


class SchemaIndex:
    """Loads ``schemas/index.json`` and resolves published schema documents.

    Entry ``path`` values are authored in the ``schemas/...`` form, so they
    resolve against the directory that contains the ``schemas/`` directory
    (the index file's grandparent). Vendoring the ``schemas/`` tree preserves
    that layout, so a relocated copy resolves identically.
    """

    def __init__(self, index_path):
        self.index_path = Path(index_path).resolve()
        if not self.index_path.is_file():
            raise ValueError(f"schema index not found: {index_path}")
        data = load_json(self.index_path)
        if not isinstance(data, dict) or not isinstance(data.get("schemas"), list):
            raise ValueError(f"malformed schema index: {index_path}")
        self.root = self.index_path.parent.parent
        self._entries: dict = {}
        for raw in data["schemas"]:
            entry = SchemaEntry(
                family=raw["family"],
                id=raw["id"],
                path=raw["path"],
                version=raw["version"],
                status=raw.get("status", ""),
                fixtures=tuple(raw.get("fixtures", [])),
            )
            self._entries[entry.family] = entry

    def families(self) -> set:
        return set(self._entries)

    def entry(self, family) -> SchemaEntry:
        if family not in self._entries:
            raise ValueError(f"unknown schema family: {family}")
        return self._entries[family]

    def schema_for(self, family) -> dict:
        return load_json(self.root / self.entry(family).path)


def load_index(index_path) -> SchemaIndex:
    return SchemaIndex(index_path)
