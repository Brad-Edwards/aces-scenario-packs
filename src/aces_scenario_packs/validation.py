"""Static, in-process validation for one untrusted scenario pack.

The public API deliberately excludes catalog discovery and author workflow
execution.  It validates only the version-matched pack contract and ACES SDL
documents, returning bounded diagnostics suitable for an ingest boundary.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from aces_sdl import SDLError, SDLParserLimits, parse_sdl, parse_sdl_file
from yaml.events import (
    AliasEvent,
    CollectionEndEvent,
    CollectionStartEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceStartEvent,
)

from . import _pack_fs

CONTENT_SAFETY_FLAGS = (
    "no_real_malware",
    "no_real_third_party_targets",
    "no_real_credentials",
    "no_sensitive_data",
    "offensive_tooling_boundary",
)
REQUIRED_REVIEW_GATES = (
    "licensing",
    "attribution",
    "sensitive-data",
    "offensive-tooling",
)

_RESOURCES = Path(__file__).with_name("resources")
_PROVENANCE_SCHEMA = _RESOURCES / "schemas" / "provenance.schema.yaml"
_COMPATIBILITY_SCHEMA = _RESOURCES / "schemas" / "pack-compatibility.schema.yaml"


@dataclass(frozen=True)
class PackValidationLimits:
    """Resource limits for one :func:`validate_pack` call."""

    max_metadata_bytes: int = 1024 * 1024
    max_sdl_bytes: int = 8 * 1024 * 1024
    max_members: int = 1024
    max_errors: int = 100
    max_error_chars: int = 240
    max_yaml_nodes: int = 20_000
    max_yaml_aliases: int = 64
    max_yaml_depth: int = 64
    sdl: SDLParserLimits = field(default_factory=SDLParserLimits)

    def __post_init__(self) -> None:
        numeric = (
            self.max_metadata_bytes,
            self.max_sdl_bytes,
            self.max_members,
            self.max_errors,
            self.max_error_chars,
            self.max_yaml_nodes,
            self.max_yaml_aliases,
            self.max_yaml_depth,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 1
            for value in numeric
        ):
            raise ValueError("pack validation limits must be positive integers")


@dataclass
class ValidationResult:
    """The deterministic outcome of validating one scenario pack."""

    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether validation completed without a contract error."""

        return not self.errors


class _Errors:
    def __init__(self, limits: PackValidationLimits) -> None:
        self._limits = limits
        self._items: list[str] = []

    def add(
        self, code: str, path: str | None = None, field_path: str | None = None
    ) -> None:
        if len(self._items) >= self._limits.max_errors:
            return
        message = code
        if path:
            message += f": {path}"
        if field_path:
            message += f":{field_path}"
        message = message[:self._limits.max_error_chars]
        self._items.append(message)

    def result(self) -> ValidationResult:
        return ValidationResult(sorted(set(self._items)))


class _DuplicateKey(yaml.YAMLError):
    pass


class _StrictLoader(yaml.SafeLoader):
    def construct_mapping(
        self, node: yaml.nodes.MappingNode, deep: bool = False
    ) -> dict[object, object]:
        mapping: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                if key in mapping:
                    raise _DuplicateKey("duplicate mapping key")
            except TypeError as exc:
                raise yaml.YAMLError("unhashable mapping key") from exc
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


@dataclass(frozen=True)
class _SchemaViolation:
    code: str
    path: str


_SCHEMA_TYPE_CHECKS = {
    "object": lambda value: isinstance(value, dict),
    "array": lambda value: isinstance(value, list),
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "null": lambda value: value is None,
}


def _resolve_ref(schema: dict[str, object], ref: str) -> dict[str, object] | None:
    if not ref.startswith("#/$defs/"):
        return None
    target: object = schema
    for part in ref[2:].split("/"):
        if not isinstance(target, dict) or part not in target:
            return None
        target = target[part]
    return target if isinstance(target, dict) else None


def _expected_types(schema: dict[str, object]) -> tuple[str, ...]:
    expected = schema.get("type")
    if expected is None:
        return ()
    if isinstance(expected, list):
        return tuple(str(item) for item in expected)
    return (str(expected),)


def _schema_violations(
    value: object,
    schema: dict[str, object],
    root_schema: dict[str, object],
    path: str = "$",
) -> list[_SchemaViolation]:
    violations: list[_SchemaViolation] = []
    ref = schema.get("$ref")
    if ref is not None:
        resolved = _resolve_ref(root_schema, str(ref))
        if resolved is None:
            return [_SchemaViolation("ref", path)]
        return _schema_violations(value, resolved, root_schema, path)

    expected = _expected_types(schema)
    if expected and not any(
        _SCHEMA_TYPE_CHECKS.get(name, lambda _value: True)(value)
        for name in expected
    ):
        return [_SchemaViolation("type", path)]
    if "const" in schema and value != schema["const"]:
        violations.append(_SchemaViolation("const", path))
    choices = schema.get("enum")
    if isinstance(choices, list) and value not in choices:
        violations.append(_SchemaViolation("enum", path))
    pattern = schema.get("pattern")
    if (
        isinstance(value, str)
        and pattern is not None
        and re.fullmatch(str(pattern), value) is None
    ):
        violations.append(_SchemaViolation("pattern", path))

    if isinstance(value, dict):
        properties = schema.get("properties")
        props = properties if isinstance(properties, dict) else {}
        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    violations.append(_SchemaViolation("required", f"{path}.{key}"))
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    violations.append(_SchemaViolation("unknown", f"{path}.{key}"))
        for key, child_schema in props.items():
            if key in value and isinstance(child_schema, dict):
                violations.extend(
                    _schema_violations(
                        value[key], child_schema, root_schema, f"{path}.{key}"
                    )
                )
    elif isinstance(value, list):
        minimum = schema.get("minItems")
        if isinstance(minimum, int) and len(value) < minimum:
            violations.append(_SchemaViolation("min-items", path))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                violations.extend(
                    _schema_violations(item, item_schema, root_schema, f"{path}[{index}]")
                )
    return violations


def _check_yaml_events(text: str, limits: PackValidationLimits) -> None:
    depth = aliases = nodes = 0
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, AliasEvent):
            aliases += 1
        if isinstance(event, (ScalarEvent, MappingStartEvent, SequenceStartEvent)):
            nodes += 1
        if isinstance(event, CollectionStartEvent):
            depth += 1
            if depth > limits.max_yaml_depth:
                raise yaml.YAMLError("YAML depth limit exceeded")
        elif isinstance(event, CollectionEndEvent):
            depth -= 1
        if (
            aliases > limits.max_yaml_aliases
            or nodes > limits.max_yaml_nodes
            or nodes * (aliases + 1) > limits.max_yaml_nodes
        ):
            raise yaml.YAMLError("YAML expansion limit exceeded")


def _load_yaml_member(
    root_fd: int,
    rel: str,
    limits: PackValidationLimits,
    errors: _Errors,
) -> object | None:
    try:
        raw = _pack_fs.read_member_bytes(
            root_fd, rel, max_bytes=limits.max_metadata_bytes
        )
        text = raw.decode("utf-8", errors="strict")
        _check_yaml_events(text, limits)
        return yaml.load(text, Loader=_StrictLoader)
    except UnicodeDecodeError:
        errors.add("yaml.invalid-utf8", rel)
    except _DuplicateKey:
        errors.add("yaml.duplicate-key", rel)
    except yaml.YAMLError:
        errors.add("yaml.invalid", rel)
    except _pack_fs.PackFilesystemError as exc:
        if str(exc) == "pack metadata exceeds the validation limit":
            errors.add("resource.metadata-limit", rel)
        else:
            errors.add("filesystem.changed", rel)
    return None


def _trusted_schema(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("packaged validation schema is not an object")
    return value


def _add_schema_violations(
    errors: _Errors,
    prefix: str,
    rel: str,
    value: object,
    schema: dict[str, object],
) -> None:
    for violation in _schema_violations(value, schema, schema):
        errors.add(f"{prefix}.schema.{violation.code}", rel, violation.path)


def _pointer(
    pack: dict[str, object],
    key: str,
    label: str,
    inventory: frozenset[str],
    errors: _Errors,
    *,
    required: bool,
    expected_path: str | None = None,
) -> str | None:
    value = pack.get(key)
    if value is None:
        if required:
            errors.add(f"{label}.pointer.missing", "pack.yaml", key)
        return None
    if not isinstance(value, str):
        errors.add(f"{label}.pointer.invalid", "pack.yaml", key)
        return None
    try:
        rel = _pack_fs.normalize_relpath(value)
    except _pack_fs.PackFilesystemError:
        errors.add(f"{label}.pointer.invalid", "pack.yaml", key)
        return None
    if expected_path is not None and rel != expected_path:
        errors.add(f"{label}.pointer.invalid", "pack.yaml", key)
        return None
    if rel not in inventory:
        errors.add(f"{label}.missing", rel)
        return None
    return rel


def _validate_provenance(
    root_fd: int,
    inventory: frozenset[str],
    pack: dict[str, object],
    limits: PackValidationLimits,
    errors: _Errors,
) -> None:
    rel = _pointer(
        pack,
        "provenance_ledger",
        "provenance",
        inventory,
        errors,
        required=True,
        expected_path="docs/provenance-ledger.yaml",
    )
    if rel is None:
        return
    ledger = _load_yaml_member(root_fd, rel, limits, errors)
    if not isinstance(ledger, dict):
        if ledger is not None:
            errors.add("provenance.type", rel)
        return
    _add_schema_violations(
        errors, "provenance", rel, ledger, _trusted_schema(_PROVENANCE_SCHEMA)
    )
    ledger_pack = ledger.get("pack")
    ledger_name = ledger_pack.get("name") if isinstance(ledger_pack, dict) else None
    if ledger_name != pack.get("name"):
        errors.add("provenance.name-mismatch", rel, "pack.name")
    safety = ledger.get("content_safety")
    for flag_name in CONTENT_SAFETY_FLAGS:
        if not isinstance(safety, dict) or safety.get(flag_name) is not True:
            errors.add("provenance.safety.required", rel, f"content_safety.{flag_name}")
    review = ledger.get("review")
    gates = review.get("gates") if isinstance(review, dict) else None
    present = (
        {
            row.get("gate_id")
            for row in gates
            if isinstance(row, dict) and isinstance(row.get("gate_id"), str)
        }
        if isinstance(gates, list)
        else set()
    )
    for gate in REQUIRED_REVIEW_GATES:
        if gate not in present:
            errors.add("provenance.review-gate.missing", rel, f"review.gates.{gate}")


def _validate_compatibility(
    root_fd: int,
    inventory: frozenset[str],
    pack: dict[str, object],
    limits: PackValidationLimits,
    errors: _Errors,
) -> None:
    rel = _pointer(
        pack, "compatibility_manifest", "compatibility", inventory, errors, required=False
    )
    if rel is None:
        return
    manifest = _load_yaml_member(root_fd, rel, limits, errors)
    if not isinstance(manifest, dict):
        if manifest is not None:
            errors.add("compatibility.type", rel)
        return
    _add_schema_violations(
        errors, "compatibility", rel, manifest, _trusted_schema(_COMPATIBILITY_SCHEMA)
    )


def _validate_pack_core(
    pack_root: str | os.PathLike[str],
    active: PackValidationLimits,
    *,
    author_sdl: bool,
) -> tuple[ValidationResult, tuple[object, ...]]:
    errors = _Errors(active)
    scenarios: tuple[object, ...] = ()
    try:
        root, root_fd = _pack_fs.open_root(pack_root)
    except _pack_fs.PackFilesystemError:
        errors.add("filesystem.invalid-root")
        return errors.result(), scenarios
    try:
        try:
            members = _pack_fs.inventory(root_fd, max_members=active.max_members)
        except _pack_fs.PackFilesystemError as exc:
            if str(exc) == "pack member count exceeds the validation limit":
                errors.add("resource.member-limit")
            else:
                errors.add("filesystem.unsafe-member")
            return errors.result(), scenarios
        inventory = frozenset(members)
        if "pack.yaml" not in inventory:
            errors.add("pack.missing", "pack.yaml")
            return errors.result(), scenarios
        pack = _load_yaml_member(root_fd, "pack.yaml", active, errors)
        if not isinstance(pack, dict):
            if pack is not None:
                errors.add("pack.type", "pack.yaml")
            return errors.result(), scenarios
        for key in ("name", "title", "version"):
            if not isinstance(pack.get(key), str) or not pack[key]:
                errors.add("pack.identity.missing", "pack.yaml", key)
        if pack.get("name") != os.path.basename(root):
            errors.add("pack.identity.name-mismatch", "pack.yaml", "name")
        _validate_provenance(root_fd, inventory, pack, active, errors)
        _validate_compatibility(root_fd, inventory, pack, active, errors)

        documents = sorted(
            rel for rel in inventory
            if rel.startswith("sdl/") and rel.count("/") == 1 and rel.endswith(".sdl.yaml")
        )
        if not documents:
            errors.add("sdl.missing", "sdl")
        parsed: list[object] = []
        for rel in documents:
            try:
                raw = _pack_fs.read_member_bytes(
                    root_fd, rel, max_bytes=active.max_sdl_bytes
                )
                text = raw.decode("utf-8", errors="strict")
                if author_sdl:
                    scenario = parse_sdl_file(
                        Path(root, *rel.split("/")), limits=active.sdl
                    )
                else:
                    scenario = parse_sdl(text, limits=active.sdl)
                parsed.append(scenario)
            except UnicodeDecodeError:
                errors.add("sdl.invalid-utf8", rel)
            except SDLError as exc:
                if not author_sdl and "imports require file-backed parsing" in str(exc):
                    errors.add("sdl.imports-denied", rel)
                else:
                    errors.add("sdl.invalid", rel)
            except OSError:
                errors.add("filesystem.changed", rel)
            except _pack_fs.PackFilesystemError as exc:
                if str(exc) == "pack metadata exceeds the validation limit":
                    errors.add("resource.sdl-limit", rel)
                else:
                    errors.add("filesystem.changed", rel)
        scenarios = tuple(parsed)
        return errors.result(), scenarios
    finally:
        os.close(root_fd)


def validate_pack(
    pack_root: str | os.PathLike[str],
    *,
    limits: PackValidationLimits | None = None,
) -> ValidationResult:
    """Validate one pack directory against the static consumer contract.

    Invalid foreign input is returned as stable, bounded error codes. Unexpected
    package defects still raise normally so they cannot be mislabeled as input
    failures.
    """

    result, _scenarios = _validate_pack_core(
        pack_root, limits or PackValidationLimits(), author_sdl=False
    )
    return result


def _validate_pack_for_author_ci(
    pack_root: str | os.PathLike[str],
    *,
    limits: PackValidationLimits | None = None,
) -> tuple[ValidationResult, tuple[object, ...]]:
    """Run the shared static authority with author-controlled import resolution."""

    return _validate_pack_core(
        pack_root, limits or PackValidationLimits(), author_sdl=True
    )


__all__ = ["PackValidationLimits", "ValidationResult", "validate_pack"]
