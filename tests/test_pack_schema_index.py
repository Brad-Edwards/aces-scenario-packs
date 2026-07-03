"""Loadability and integrity gates for the scenario-pack schemas (ASP-0004).

These tests keep the published schema set honest without pulling a third-party
JSON Schema engine (the repo is stdlib-only and validation tooling is deferred to
Brad-Edwards/aces-scenario-packs#5). They assert, using ordinary assertions:

- ``schemas/index.json`` exists, parses, and is the source of truth for every
  published schema (no orphan schema files on disk, no dangling index entries).
- every index entry carries source, ownership, and compatibility-impact notes.
- every schema file is loadable JSON and a well-formed JSON Schema document whose
  ``$id`` / ``version`` match its index entry.
- every schema ships at least one fixture that is loadable and *conforms* to the
  schema. Conformance is checked by a small recursive checker covering exactly
  the JSON Schema keywords these schemas use; a coverage guard fails if any
  schema introduces a keyword the checker does not handle, so conformance
  coverage can never silently go vacuous.
- the nine schema families named by ASP-0004 are all present.
"""

from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
INDEX = SCHEMA_DIR / "index.json"

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"

# The families ASP-0004 requires this repository to define or host.
REQUIRED_FAMILIES = {
    "pack-metadata",
    "compatibility",
    "provenance",
    "artifact-boundary",
    "runtime-profile",
    "delivery-bundle",
    "lifecycle",
    "validation",
    "release",
}

# JSON Schema keywords the conformance checker below understands. Any keyword
# used by a published schema but absent here is a coverage gap and fails
# ``test_checker_covers_every_keyword_used`` rather than passing silently.
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


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _type_matches(value, declared) -> bool:
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


def _conformance_errors(instance, schema, where="<root>"):
    """Return a list of human-readable conformance errors for ``instance``.

    Recursive over the keyword subset in ``SUPPORTED_KEYWORDS``. This is not a
    general JSON Schema validator; it is exactly enough to prove the shipped
    fixtures satisfy the shipped schemas, guarded by the keyword-coverage test.
    """
    errors: list[str] = []

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{where}: expected const {schema['const']!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{where}: {instance!r} not in enum {schema['enum']!r}")

    declared = schema.get("type")
    if declared is not None and not _type_matches(instance, declared):
        errors.append(f"{where}: {instance!r} is not of type {declared!r}")
        return errors  # further keyword checks assume the declared shape

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{where}: missing required property {key!r}")
        props = schema.get("properties", {})
        for key, subschema in props.items():
            if key in instance:
                errors.extend(
                    _conformance_errors(instance[key], subschema, f"{where}.{key}")
                )
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(props))
            if extra:
                errors.append(f"{where}: unexpected properties {extra}")

    if isinstance(instance, list):
        item_schema = schema.get("items")
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(
                f"{where}: has {len(instance)} items, fewer than minItems "
                f"{schema['minItems']}"
            )
        if isinstance(item_schema, dict):
            for idx, item in enumerate(instance):
                errors.extend(
                    _conformance_errors(item, item_schema, f"{where}[{idx}]")
                )

    return errors


def _collect_keywords(schema, seen: set) -> None:
    if isinstance(schema, dict):
        for key, value in schema.items():
            seen.add(key)
            if key == "properties" and isinstance(value, dict):
                for sub in value.values():
                    _collect_keywords(sub, seen)
            elif key == "items":
                _collect_keywords(value, seen)
            elif isinstance(value, dict):
                _collect_keywords(value, seen)


class SchemaIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = _load_json(INDEX) if INDEX.exists() else {}
        cls.entries = cls.index.get("schemas", []) if isinstance(cls.index, dict) else []

    def test_index_exists_and_parses(self) -> None:
        self.assertTrue(INDEX.exists(), f"missing schema index: {INDEX}")
        self.assertIsInstance(self.index, dict, "index.json is not a JSON object")
        self.assertTrue(self.entries, "schema index lists no schemas")

    def test_required_families_present(self) -> None:
        families = {entry.get("family") for entry in self.entries}
        missing = sorted(REQUIRED_FAMILIES - families)
        self.assertEqual([], missing, f"index missing required families: {missing}")

    def test_no_orphan_schema_files(self) -> None:
        on_disk = {p.relative_to(ROOT).as_posix() for p in SCHEMA_DIR.glob("*.schema.json")}
        indexed = {entry.get("path") for entry in self.entries}
        orphans = sorted(on_disk - indexed)
        self.assertEqual([], orphans, f"schema files not listed in index: {orphans}")

    def test_entries_have_source_and_ownership_notes(self) -> None:
        for entry in self.entries:
            with self.subTest(family=entry.get("family")):
                for field in ("family", "id", "path", "version", "status",
                              "source", "ownership", "compatibility_impact", "fixtures"):
                    value = entry.get(field)
                    self.assertNotIn(
                        value, (None, "", []),
                        f"index entry {entry.get('family')!r} missing {field!r}",
                    )

    def test_schemas_are_loadable_and_well_formed(self) -> None:
        for entry in self.entries:
            with self.subTest(family=entry.get("family")):
                path = ROOT / entry["path"]
                self.assertTrue(path.exists(), f"schema file missing: {path}")
                schema = _load_json(path)
                self.assertEqual(schema.get("$schema"), DRAFT_2020_12,
                                 f"{entry['family']}: wrong or missing $schema")
                self.assertEqual(schema.get("$id"), entry["id"],
                                 f"{entry['family']}: $id does not match index id")
                self.assertEqual(schema.get("version"), entry["version"],
                                 f"{entry['family']}: version does not match index")
                self.assertTrue(schema.get("title"), f"{entry['family']}: missing title")
                self.assertIn("type", schema, f"{entry['family']}: missing top-level type")

    def test_checker_covers_every_keyword_used(self) -> None:
        used: set[str] = set()
        for entry in self.entries:
            _collect_keywords(_load_json(ROOT / entry["path"]), used)
        unsupported = sorted(used - SUPPORTED_KEYWORDS)
        self.assertEqual(
            [], unsupported,
            f"schemas use JSON Schema keywords the conformance checker does not "
            f"handle: {unsupported} (extend SUPPORTED_KEYWORDS and the checker)",
        )

    def test_fixtures_are_loadable_and_conform(self) -> None:
        for entry in self.entries:
            schema = _load_json(ROOT / entry["path"])
            for fixture_path in entry["fixtures"]:
                with self.subTest(family=entry.get("family"), fixture=fixture_path):
                    path = ROOT / fixture_path
                    self.assertTrue(path.exists(), f"fixture missing: {path}")
                    instance = _load_json(path)
                    errors = _conformance_errors(instance, schema)
                    self.assertEqual([], errors, f"{fixture_path} does not conform: {errors}")


class ConformanceCheckerTests(unittest.TestCase):
    """Pin the conformance checker's teeth against synthetic inputs.

    ``SchemaIndexTests`` only ever asserts that conforming fixtures yield *no*
    errors, so a checker regressed to ``return []`` would pass it silently.
    These tests assert the checker produces errors for genuinely invalid input
    for every keyword it claims to support, so a broken or no-op checker fails
    here. Each case names the keyword and the path it should flag.
    """

    def test_valid_instance_yields_no_errors(self) -> None:
        schema = {
            "type": "object",
            "required": ["a"],
            "properties": {
                "a": {"type": "string", "enum": ["x", "y"]},
                "b": {"type": "array", "minItems": 1, "items": {"type": "integer"}},
            },
            "additionalProperties": False,
        }
        instance = {"a": "x", "b": [1, 2]}
        self.assertEqual([], _conformance_errors(instance, schema))

    def test_missing_required_is_flagged(self) -> None:
        errors = _conformance_errors({}, {"type": "object", "required": ["a"]})
        self.assertTrue(errors)
        self.assertIn("required", errors[0])

    def test_wrong_type_is_flagged(self) -> None:
        errors = _conformance_errors(1, {"type": "string"})
        self.assertTrue(errors)
        self.assertIn("type", errors[0])

    def test_boolean_is_not_a_number(self) -> None:
        # bool is a subclass of int in Python; the JSON distinction must hold.
        self.assertTrue(_conformance_errors(True, {"type": "integer"}))
        self.assertEqual([], _conformance_errors(1, {"type": "integer"}))

    def test_enum_violation_is_flagged(self) -> None:
        errors = _conformance_errors("z", {"enum": ["x", "y"]})
        self.assertTrue(errors)
        self.assertIn("enum", errors[0])

    def test_const_violation_is_flagged(self) -> None:
        errors = _conformance_errors(False, {"const": True})
        self.assertTrue(errors)
        self.assertIn("const", errors[0])

    def test_min_items_violation_is_flagged(self) -> None:
        errors = _conformance_errors([], {"type": "array", "minItems": 1})
        self.assertTrue(errors)
        self.assertIn("minItems", errors[0])

    def test_additional_properties_false_is_flagged(self) -> None:
        schema = {"type": "object", "properties": {"a": {"type": "string"}},
                  "additionalProperties": False}
        errors = _conformance_errors({"a": "x", "extra": 1}, schema)
        self.assertTrue(errors)
        self.assertIn("unexpected", errors[0])

    def test_nested_property_error_carries_path(self) -> None:
        schema = {
            "type": "object",
            "properties": {"outer": {"type": "object", "required": ["inner"]}},
        }
        errors = _conformance_errors({"outer": {}}, schema)
        self.assertTrue(errors)
        self.assertIn("outer", errors[0])

    def test_array_item_error_carries_index(self) -> None:
        schema = {"type": "array", "items": {"type": "string"}}
        errors = _conformance_errors(["ok", 2], schema)
        self.assertTrue(errors)
        self.assertIn("[1]", errors[0])

    def test_keyword_collector_finds_nested_keywords(self) -> None:
        # The coverage guard relies on this walking into properties and items.
        seen: set[str] = set()
        _collect_keywords(
            {"type": "object", "properties": {"a": {"type": "array",
             "items": {"minItems": 0}}}},
            seen,
        )
        for keyword in ("type", "properties", "items", "minItems"):
            self.assertIn(keyword, seen)


if __name__ == "__main__":
    unittest.main()
