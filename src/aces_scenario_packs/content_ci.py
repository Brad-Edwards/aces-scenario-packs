#!/usr/bin/env python3
"""Repo-wide scenario-content gate (issue #138).

Mechanically enforces the scenario-pack contract that was previously "enforced
by review" — so a regression cannot ship just because a reviewer forgot to run
the validators. Runs the same checks for EVERY pack under ``scenarios/<name>/``,
so every present and future pack benefits:

  1. **Validators** — every ``scenarios/*/sdl/validate_*.py validate`` exits 0.
  2. **Test suites** — every ``scenarios/*/sdl/tests``,
     ``scenarios/*/build/tests``, ``scenarios/*/profiles/tests``, and
     ``scenarios/*/ctfd/tests`` unittest suite passes.
  3. **Visibility / leak scan** — no operator token (oracle ``S-*`` states,
     ``<n>.<L>`` step ids, ATT&CK technique ids, ``S1.*``/``S2.*`` source
     labels) appears in any participant-facing surface (``assets/content/**``,
     ``assets/briefing/**``). This is *"the single most important invariant of
     the pack"* (scenario-design.md) — a leaked hidden-path token hands
     participants the solution.
  4. **Manifest** — every pack ships a ``pack.yaml``.
  5. **Golden checklist** — every pack carries
     ``docs/golden-readiness-checklist.md`` so final manual participant review
     is planned and auditable.
  6. **Shared oracle model** — the reusable operator/oracle-only model bundled
     with this package validates its fixtures and tests without being treated as
     a scenario pack.

Stdlib + PyYAML only. Run locally exactly as CI does:

    aces-pack-validate --repo .
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

import yaml

from collections.abc import Iterator

# Canonical contract resources ship inside this installed package (schemas,
# template, oracle fixtures + model). They are resolved relative to the package,
# never the consumer's working tree.
_PKG = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_PKG, "resources")
_SCHEMAS_DIR = os.path.join(_RES, "schemas")
_TEMPLATE_DIR = os.path.join(_RES, "template")
_ORACLE_DIR = os.path.join(_RES, "oracle")

# The catalog under validation is the consumer's tree: <_REPO>/scenarios/<pack>/.
# Defaults to the current directory; override with --repo, or by setting these
# module globals directly (tests do this).
_REPO = os.getcwd()
SCEN = os.path.join(_REPO, "scenarios")

COMPATIBILITY_MANIFEST_FILE = "pack.compatibility.yaml"
PACK_MANIFEST_FILE = "pack.yaml"
COMPATIBILITY_SCHEMA_FILE = "pack-compatibility.schema.yaml"
PROVENANCE_SCHEMA_FILE = "provenance.schema.yaml"
# Display labels for the packaged example fixtures (used in messages only).
COMPATIBILITY_EXAMPLE_FILE = os.path.join("template", "pack.compatibility.example.yaml")
PROVENANCE_EXAMPLE_FILE = os.path.join("template", "docs", "provenance-ledger.example.yaml")
# Safety attestations that must all be true to ship — the policy is EXCLUSION of
# real sensitive content, never a weaker classification.
CONTENT_SAFETY_FLAGS = (
    "no_real_malware",
    "no_real_third_party_targets",
    "no_real_credentials",
    "no_sensitive_data",
    "offensive_tooling_boundary",
)
# Publication-review gates the ledger must cover (acceptance criterion: a review
# checklist covering licensing, attribution, sensitive data, and offensive
# tooling boundaries). `customer-overlay` is an optional extra gate.
REQUIRED_REVIEW_GATES = ("licensing", "attribution", "sensitive-data", "offensive-tooling")


def compatibility_schema_path() -> str:
    """Compatibility schema path."""
    return os.path.join(_SCHEMAS_DIR, "pack-compatibility.schema.yaml")


def compatibility_example_path() -> str:
    """Compatibility example path."""
    return os.path.join(_TEMPLATE_DIR, "pack.compatibility.example.yaml")


def provenance_schema_path() -> str:
    """Provenance schema path."""
    return os.path.join(_SCHEMAS_DIR, "provenance.schema.yaml")


def provenance_example_path() -> str:
    """Provenance example path."""
    return os.path.join(_TEMPLATE_DIR, "docs", "provenance-ledger.example.yaml")

# Packs are scenarios/<name>/ with a pack.yaml. `_template` is a scaffold and
# `_oracle` is the shared oracle model, not packs; the gate skips both.
SKIP = {"_template", "_oracle"}

# Operator tokens that must never reach participant-facing surfaces.
TOKEN_PATTERNS = [
    (re.compile(r"\bS-[A-Z]{3,}\b"), "oracle S-* state"),
    (re.compile(r"\bS[12]\.\d{1,2}\b"), "source label S1.*/S2.*"),
    (re.compile(r"\bT\d{4}(?:\.\d{3})?\b"), "ATT&CK technique id"),
    (re.compile(r"(?<![\w.])(?:10|[1-9])\.[A-Z](?![\w])"), "attack-path step id"),
]
WIZARD_SPIDER_STALE_MILESTONES = re.compile(
    r"(?<!\d)#(?:36|37|52)\b|issues/(?:36|37|52)\b"
)
PARTICIPANT_DIRS = [
    ("assets", "content"),
    ("assets", "briefing"),
    ("challenges",),
]
TEXT_EXT = {".md", ".txt", ".yaml", ".yml", ".csv", ".json", ".log", ".note"}


def _git_lines(args: list[str]) -> list[str]:
    """Git lines."""
    try:
        r = subprocess.run(
            ["git", "-C", _REPO, *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if r.returncode != 0:
        return []
    return [line for line in r.stdout.splitlines() if line.strip()]


def _is_git_visible_pack_dir(name: str) -> bool:
    """Is git visible pack dir."""
    if (_git_lines(["rev-parse", "--is-inside-work-tree"]) != ["true"]
            or os.path.abspath(SCEN) != os.path.join(os.path.abspath(_REPO), "scenarios")):
        return True
    rel = os.path.join("scenarios", name)
    # Tracked (ls-files) or new local work not yet ignored, so developers still
    # get manifest/checklist failures before the first commit. Ignored
    # cache-only directories (stray __pycache__) are excluded by git.
    return bool(_git_lines(["ls-files", "--", rel])
                or _git_lines(["status", "--porcelain", "--untracked-files=all", "--", rel]))


def _packs() -> list[str]:
    """Packs."""
    if not os.path.isdir(SCEN):
        return []
    out = []
    for name in sorted(os.listdir(SCEN)):
        p = os.path.join(SCEN, name)
        if name in SKIP or not os.path.isdir(p):
            continue
        if (not os.path.isfile(os.path.join(p, PACK_MANIFEST_FILE))
                and not _is_git_visible_pack_dir(name)):
            continue
        out.append(name)
    return out


# Directories under a pack that ship static `validate_*.py validate` gates. The
# sdl ledgers (#21–#24) and the delivery-profile bundles (#50) both ship one.
VALIDATOR_DIRS = ("sdl", "profiles")


def _run_one_validator(vdir: str, fname: str, tag: str, failures: list[str]) -> None:
    """Run one validator."""
    r = subprocess.run([sys.executable, os.path.join(vdir, fname), "validate"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        failures.append(f"validator FAILED: {tag}\n{r.stdout[-800:]}{r.stderr[-800:]}")
    else:
        print(f"  [ok] {tag}")


def _check_validator_dir(pack: str, sub: str, failures: list[str]) -> None:
    """Check validator dir."""
    vdir = os.path.join(SCEN, pack, sub)
    if not os.path.isdir(vdir):
        return
    for fname in sorted(os.listdir(vdir)):
        if fname.startswith("validate_") and fname.endswith(".py"):
            _run_one_validator(vdir, fname, f"{pack}/{sub}/{fname}", failures)


def check_validators(failures: list[str]) -> None:
    """Check validators."""
    for pack in _packs():
        for sub in VALIDATOR_DIRS:
            _check_validator_dir(pack, sub, failures)


def check_tests(failures: list[str]) -> None:
    """Check tests."""
    for pack in _packs():
        for sub in ("sdl/tests", "build/tests", "profiles/tests", "ctfd/tests"):
            d = os.path.join(SCEN, pack, sub)
            if not os.path.isdir(d):
                continue
            r = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", d],
                capture_output=True, text=True, cwd=_REPO)
            tag = f"{pack}/{sub}"
            if r.returncode != 0:
                failures.append(f"tests FAILED: {tag}\n{r.stderr[-1200:]}")
            else:
                print(f"  [ok] {tag} ({r.stderr.strip().splitlines()[-1] if r.stderr else 'ok'})")


def _iter_text_files(root: str) -> Iterator[str]:
    """Yield every text-extension file under ``root`` (recursive)."""
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if os.path.splitext(name)[1].lower() in TEXT_EXT:
                yield os.path.join(dirpath, name)


def _token_leaks(path: str) -> list[tuple[str, int]]:
    """Return ``(label, line_no)`` for every operator token class found in ``path``.

    The match is reported only by its *class* and a token-independent locator
    (the 1-based line of the first hit). The scan exists to keep operator tokens
    off participant-facing surfaces; the CI log is itself a quasi-public surface,
    so the report must not disclose the match (issue #138). Echoing the raw match
    obviously leaks it, but so does any token-*derived* verifier: the scanned
    vocabularies (oracle ``S-*`` states, ATT&CK technique ids, step ids) are
    low-entropy, so even a truncated hash is reversible by precomputation. The
    class label plus ``path:line`` is enough for an operator to find the match
    locally without the gate disclosing it.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        body = fh.read()
    leaks: list[tuple[str, int]] = []
    for pat, label in TOKEN_PATTERNS:
        if m := pat.search(body):
            leaks.append((label, body.count("\n", 0, m.start()) + 1))
    return leaks


def _participant_roots(pack: str) -> list[str]:
    """Absolute participant-facing roots for a pack.

    The fixed assets surfaces, plus — by convention — the delivery-profile
    participant surfaces (#50): ``profiles/_shared`` and every
    ``profiles/<bundle>/participant`` directory. Operator bundle dirs
    (``profiles/<bundle>/operator``) are intentionally excluded; they may
    legitimately cite the oracle. New bundles are covered automatically.
    """
    roots = [os.path.join(SCEN, pack, *parts) for parts in PARTICIPANT_DIRS]
    profiles = os.path.join(SCEN, pack, "profiles")
    if os.path.isdir(profiles):
        shared = os.path.join(profiles, "_shared")
        if os.path.isdir(shared):
            roots.append(shared)
        for entry in sorted(os.listdir(profiles)):
            part = os.path.join(profiles, entry, "participant")
            if os.path.isdir(part):
                roots.append(part)
    return roots


def check_visibility(failures: list[str]) -> None:
    """Check visibility."""
    for pack in _packs():
        for root in _participant_roots(pack):
            if not os.path.isdir(root):
                continue
            for fp in _iter_text_files(root):
                for label, line_no in _token_leaks(fp):
                    rel = os.path.relpath(fp, _REPO)
                    failures.append(
                        f"VISIBILITY LEAK: {rel}:{line_no} contains a {label} "
                        f"(match redacted) in a participant-facing file")
            print(f"  [ok] {os.path.relpath(root, SCEN)} clean")


def _wizard_spider_drift_files() -> list[str]:
    """Files where the closed Wizard Spider milestone plan must not reappear."""
    roots = [os.path.join(SCEN, "wizard-spider")]
    files: list[str] = []
    for root in roots:
        if os.path.isdir(root):
            files.extend(_iter_text_files(root))
    original_preflight = os.path.join(
        SCEN, "design-notes", "wizard-spider-scenario-contract-preflight-32.md")
    if os.path.isfile(original_preflight):
        files.append(original_preflight)
    return sorted(set(files))


def check_wizard_spider_pack_drift(failures: list[str]) -> None:
    """Block reintroducing the closed scoring/profile milestone plan.

    Issue #207 replaced the canceled Wizard Spider scoring/profile/runtime plan
    with the current pack-layer sequence (#208-#214). This gate is deliberately
    narrow: it prevents stale closed issue references from steering future
    Wizard Spider work back toward #36/#37/#52, while leaving other packs'
    historical scoring/profile layers untouched.
    """
    scanned = 0
    for fp in _wizard_spider_drift_files():
        scanned += 1
        with open(fp, "r", encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        if m := WIZARD_SPIDER_STALE_MILESTONES.search(body):
            rel = os.path.relpath(fp, _REPO)
            line_no = body.count("\n", 0, m.start()) + 1
            failures.append(
                f"WIZARD-SPIDER PACK DRIFT: {rel}:{line_no} references the "
                "closed #36/#37/#52 scoring/profile plan; use the current "
                "#208-#214 pack-layer sequence")
    if scanned:
        print(f"  [ok] wizard-spider pack drift scan ({scanned} files)")


def _shared_oracle_model_file() -> str:
    """Shared oracle model file."""
    return os.path.join(_PKG, "oracle_model.py")


def _shared_oracle_fixture_paths() -> list[str]:
    """Shared oracle fixture paths."""
    fixtures = os.path.join(_ORACLE_DIR, "fixtures")
    if not os.path.isdir(fixtures):
        return []
    return [
        os.path.join(fixtures, name)
        for name in sorted(os.listdir(fixtures))
        if name.endswith((".yaml", ".yml"))
    ]


def check_shared_oracle_model(failures: list[str]) -> None:
    """Smoke-check the packaged shared oracle model against its shipped fixtures.

    The model and fixtures ship inside this package; the package's own test suite
    exercises the model's behaviour. This gate only confirms the shipped model
    validates its shipped fixtures, so a broken release is caught in the field.
    """
    model = _shared_oracle_model_file()
    fixtures = _shared_oracle_fixture_paths()

    if not os.path.isfile(model):
        failures.append("shared oracle model MISSING from package")
        return
    if not fixtures:
        failures.append("shared oracle fixtures MISSING from package")
        return

    r = subprocess.run(
        [sys.executable, model, "validate", *fixtures],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        failures.append(
            "shared oracle fixtures FAILED:\n"
            f"{r.stdout[-1200:]}{r.stderr[-1200:]}")
    else:
        print(f"  [ok] shared oracle fixtures ({len(fixtures)} files)")


def _load_yaml(path: str, failures: list[str], label: str) -> object:
    """Load yaml."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        failures.append(f"{label} INVALID: {path}: {exc}")
        return None


def _resolve_ref(schema: dict[str, object], ref: str) -> dict[str, object] | None:
    """Resolve ref."""
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        return None
    target: object = schema
    for part in ref[len("#/"):].split("/"):
        if not isinstance(target, dict) or part not in target:
            return None
        target = target[part]
    return target if isinstance(target, dict) else None


_SCHEMA_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}

# Order matters: bool is a subclass of int, so it must be checked first.
_SCHEMA_TYPE_LABELS = (
    (bool, "boolean"),
    (int, "integer"),
    (str, "string"),
    (list, "array"),
    (dict, "object"),
)


def _schema_type_ok(value: object, type_name: str) -> bool:
    """Schema type ok."""
    return _SCHEMA_TYPE_CHECKS.get(type_name, lambda _v: True)(value)


def _schema_type_label(value: object) -> str:
    """Schema type label."""
    if value is None:
        return "null"
    for py_type, label in _SCHEMA_TYPE_LABELS:
        if isinstance(value, py_type):
            return label
    return type(value).__name__


def _schema_expected_types(schema: dict[str, object]) -> list[str] | None:
    """Schema expected types."""
    expected = schema.get("type")
    if expected is None:
        return None
    if isinstance(expected, list):
        return [str(t) for t in expected]
    return [str(expected)]


def _validate_schema_type(value: object, schema: dict[str, object], path: str,
                          errors: list[str]) -> bool:
    """Validate schema type."""
    expected_types = _schema_expected_types(schema)
    if expected_types is None:
        return True
    if any(_schema_type_ok(value, t) for t in expected_types):
        return True
    errors.append(
        f"{path}: expected {'/'.join(expected_types)}, got "
        f"{_schema_type_label(value)}")
    return False


def _validate_schema_value_constraints(value: object, schema: dict[str, object],
                                       path: str, errors: list[str]) -> None:
    """Validate schema value constraints."""
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: unsupported value {value!r}")
    if isinstance(value, str) and "pattern" in schema:
        if not re.fullmatch(str(schema["pattern"]), value):
            errors.append(f"{path}: does not match required pattern")


def _schema_properties(schema: dict[str, object]) -> dict[str, object]:
    """Schema properties."""
    props = schema.get("properties", {})
    return props if isinstance(props, dict) else {}


def _validate_required_fields(value: dict[str, object], schema: dict[str, object],
                              path: str, errors: list[str]) -> None:
    """Validate required fields."""
    required = schema.get("required", [])
    if not isinstance(required, list):
        return
    for key in required:
        if key not in value:
            errors.append(f"{path}.{key}: required field missing")


def _validate_known_fields(value: dict[str, object], schema: dict[str, object],
                           props: dict[str, object], path: str,
                           errors: list[str]) -> None:
    """Validate known fields."""
    if schema.get("additionalProperties") is not False:
        return
    for key in value:
        if key not in props:
            errors.append(f"{path}.{key}: unknown field")


def _validate_schema_object(value: dict[str, object], schema: dict[str, object],
                            root_schema: dict[str, object], path: str,
                            errors: list[str]) -> None:
    """Validate schema object."""
    props = _schema_properties(schema)
    _validate_required_fields(value, schema, path, errors)
    _validate_known_fields(value, schema, props, path, errors)
    for key, child_schema in props.items():
        if key in value and isinstance(child_schema, dict):
            _validate_json_schema_subset(
                value[key], child_schema, root_schema, f"{path}.{key}", errors)


def _validate_schema_array(value: list[object], schema: dict[str, object],
                           root_schema: dict[str, object], path: str,
                           errors: list[str]) -> None:
    """Validate schema array."""
    if "minItems" in schema and len(value) < int(schema["minItems"]):
        errors.append(f"{path}: expected at least {schema['minItems']} item(s)")
    item_schema = schema.get("items")
    if not isinstance(item_schema, dict):
        return
    for idx, item in enumerate(value):
        _validate_json_schema_subset(item, item_schema, root_schema, f"{path}[{idx}]",
                                     errors)


def _validate_json_schema_subset(value: object, schema: dict[str, object],
                                 root_schema: dict[str, object], path: str,
                                 errors: list[str]) -> None:
    """Validate json schema subset."""
    if "$ref" in schema:
        resolved = _resolve_ref(root_schema, str(schema["$ref"]))
        if resolved is None:
            errors.append(f"{path}: unresolved schema ref {schema['$ref']}")
            return
        _validate_json_schema_subset(value, resolved, root_schema, path, errors)
        return

    if not _validate_schema_type(value, schema, path, errors):
        return

    _validate_schema_value_constraints(value, schema, path, errors)
    if isinstance(value, dict):
        _validate_schema_object(value, schema, root_schema, path, errors)
    if isinstance(value, list):
        _validate_schema_array(value, schema, root_schema, path, errors)


def _path_inside_pack(pack_root: str, rel_path: str) -> bool:
    """Path inside pack."""
    if not rel_path or os.path.isabs(rel_path):
        return False
    root = os.path.abspath(pack_root)
    target = os.path.abspath(os.path.join(root, rel_path))
    return os.path.commonpath([root, target]) == root


def _iter_path_fields(value: object, path: str = "$") -> Iterator[tuple[str, object]]:
    """Iter path fields."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "path" and isinstance(child, str):
                yield child_path, child
            yield from _iter_path_fields(child, child_path)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            yield from _iter_path_fields(child, f"{path}[{idx}]")


def _get_nested(value: dict[str, object], dotted: str) -> object:
    """Get nested."""
    cur: object = value
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _norm_manifest_path(rel_path: str) -> str:
    """Norm manifest path."""
    return os.path.normpath(rel_path).rstrip(os.sep)


def _path_is_parent(parent: str, child: str) -> bool:
    """Path is parent."""
    parent_norm = _norm_manifest_path(parent)
    child_norm = _norm_manifest_path(child)
    if parent_norm in ("", ".") or parent_norm == child_norm:
        return False
    return child_norm.startswith(parent_norm + os.sep)


BOUNDARY_GROUPS = ("oracle_only", "participant_visible", "operator_only", "commercial")
EXPOSED_BOUNDARY_GROUPS = ("participant_visible", "operator_only", "commercial")
PRIVATE_BOUNDARY_EXPORTS = {"oracle", "private"}


def _iter_boundary_rows(boundaries: dict[str, object], group: str) -> Iterator[dict[str, object]]:
    """Iter boundary rows."""
    rows = boundaries.get(group, [])
    if not isinstance(rows, list):
        return
    for row in rows:
        if isinstance(row, dict):
            yield row


def _boundary_path(row: dict[str, object]) -> str | None:
    """Boundary path."""
    path = row.get("path")
    return path if isinstance(path, str) else None


def _is_private_boundary(group: str, row: dict[str, object]) -> bool:
    """Is private boundary."""
    return group == "oracle_only" or row.get("export") in PRIVATE_BOUNDARY_EXPORTS


def _private_boundary_paths(boundaries: dict[str, object]) -> list[str]:
    """Private boundary paths."""
    private_paths: list[str] = []
    for group in BOUNDARY_GROUPS:
        for row in _iter_boundary_rows(boundaries, group):
            path = _boundary_path(row)
            if path is not None and _is_private_boundary(group, row):
                private_paths.append(path)
    return private_paths


def _iter_exposed_boundary_paths(boundaries: dict[str, object]) -> Iterator[tuple[str, str]]:
    """Iter exposed boundary paths."""
    for group in EXPOSED_BOUNDARY_GROUPS:
        for row in _iter_boundary_rows(boundaries, group):
            path = _boundary_path(row)
            if path is not None and not _is_private_boundary(group, row):
                yield group, path


def _record_boundary_overlap(failures: list[str], pack: str, group: str,
                             exposed_path: str, private_path: str) -> None:
    """Record boundary overlap."""
    failures.append(
        f"compatibility manifest INVALID: {pack}: {group} path "
        f"{exposed_path} contains oracle/private path {private_path}")


def _check_boundary_overlaps(manifest: dict[str, object], failures: list[str],
                             pack: str) -> None:
    """Check boundary overlaps."""
    boundaries = manifest.get("artifact_boundaries")
    if not isinstance(boundaries, dict):
        return
    private_paths = _private_boundary_paths(boundaries)
    for group, exposed_path in _iter_exposed_boundary_paths(boundaries):
        for private_path in private_paths:
            if _path_is_parent(exposed_path, private_path):
                _record_boundary_overlap(failures, pack, group, exposed_path,
                                         private_path)


def _check_duplicate_ids(manifest: dict[str, object], failures: list[str], pack: str) -> None:
    """Check duplicate ids."""
    checks = [
        ("runtime_profiles", "profile_id"),
        ("delivery_bundles", "bundle_id"),
        ("platform_features", "feature_id"),
        ("assets", "asset_id"),
        ("operator_surfaces", "surface_id"),
        ("validation.commands", "id"),
        ("validation.gates", "id"),
    ]
    for dotted, id_key in checks:
        rows = _get_nested(manifest, dotted)
        if not isinstance(rows, list):
            continue
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get(id_key), str):
                continue
            value = row[id_key]
            if value in seen:
                failures.append(
                    f"compatibility manifest INVALID: {pack}: duplicate {id_key} {value}")
            seen.add(value)


def _load_pack_doc(pack: str, pack_yaml: dict[str, object], key: str,
                   label: str, schema_path: str, failures: list[str], *,
                   required: bool) -> tuple[dict[str, object], dict[str, object], str] | None:
    """Load a pack-referenced YAML doc and its schema, or None (recording a failure)."""
    pack_root = os.path.join(SCEN, pack)
    rel = pack_yaml.get(key)
    if not isinstance(rel, str) or not _path_inside_pack(pack_root, rel):
        if rel is not None:
            failures.append(f"{label} INVALID: {pack}: {key} path escapes pack root")
        elif required:
            failures.append(
                f"{label} MISSING: scenarios/{pack}/{PACK_MANIFEST_FILE} has no {key} pointer")
        return None
    path = os.path.join(pack_root, rel)
    schema = manifest = None
    if os.path.isfile(path):
        schema = _load_yaml(schema_path, failures, f"{label} schema")
        manifest = _load_yaml(path, failures, label)
    if not isinstance(schema, dict) or not isinstance(manifest, dict):
        state = "MISSING" if not os.path.isfile(path) else "INVALID"
        failures.append(f"{label} {state}: scenarios/{pack}/{rel}")
        return None
    return schema, manifest, rel


def _validate_compatibility_manifest(pack: str, pack_yaml: dict[str, object],
                                     failures: list[str]) -> None:
    """Validate compatibility manifest."""
    pack_root = os.path.join(SCEN, pack)
    loaded = _load_pack_doc(pack, pack_yaml, "compatibility_manifest",
                            "compatibility manifest", compatibility_schema_path(),
                            failures, required=False)
    if loaded is None:
        return
    schema, manifest, manifest_rel = loaded

    errors: list[str] = []
    _validate_json_schema_subset(manifest, schema, schema, "$", errors)
    for error in errors:
        failures.append(
            f"compatibility manifest INVALID: scenarios/{pack}/{manifest_rel}: {error}")

    manifest_name = _get_nested(manifest, "pack.name")
    pack_name = pack_yaml.get("name")
    if manifest_name != pack_name:
        failures.append(
            f"compatibility manifest INVALID: {pack}: pack name mismatch "
            f"{PACK_MANIFEST_FILE}={pack_name!r} compatibility={manifest_name!r}")

    _check_duplicate_ids(manifest, failures, pack)
    _check_boundary_overlaps(manifest, failures, pack)
    for field_path, rel_path in _iter_path_fields(manifest):
        if not _path_inside_pack(pack_root, rel_path):
            failures.append(
                f"compatibility manifest INVALID: {pack}: {field_path} path "
                "escapes pack root")
            continue
        if not os.path.exists(os.path.join(pack_root, rel_path)):
            failures.append(
                f"compatibility manifest INVALID: {pack}: {field_path} "
                f"references missing path {rel_path}")


def check_compatibility_schema_example(failures: list[str]) -> None:
    """Check compatibility schema example."""
    schema = _load_yaml(compatibility_schema_path(), failures, "compatibility schema")
    example = _load_yaml(compatibility_example_path(), failures, "compatibility example")
    if not isinstance(schema, dict) or not isinstance(example, dict):
        failures.append("compatibility example INVALID: schema or example is not an object")
        return
    errors: list[str] = []
    _validate_json_schema_subset(example, schema, schema, "$", errors)
    for error in errors:
        failures.append(
            f"compatibility example INVALID: {COMPATIBILITY_EXAMPLE_FILE}: {error}")
    if not errors:
        print("  [ok] _template/pack.compatibility.example.yaml")


def check_manifest(failures: list[str]) -> None:
    """Check manifest."""
    check_compatibility_schema_example(failures)
    for pack in _packs():
        pack_yaml_path = os.path.join(SCEN, pack, PACK_MANIFEST_FILE)
        if not os.path.isfile(pack_yaml_path):
            failures.append(f"manifest MISSING: scenarios/{pack}/{PACK_MANIFEST_FILE}")
            continue
        pack_yaml = _load_yaml(pack_yaml_path, failures, "manifest")
        if not isinstance(pack_yaml, dict):
            failures.append(f"manifest INVALID: scenarios/{pack}/{PACK_MANIFEST_FILE}")
            continue
        _validate_compatibility_manifest(pack, pack_yaml, failures)
        print(f"  [ok] {pack}/{PACK_MANIFEST_FILE}")


def _check_provenance_duplicate_ids(ledger: dict[str, object], failures: list[str],
                                    pack: str) -> None:
    """Check provenance duplicate ids."""
    for key, id_key in (("sources", "source_id"), ("artifacts", "artifact_id"),
                        ("overlays", "overlay_id")):
        rows = ledger.get(key)
        if not isinstance(rows, list):
            continue
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get(id_key), str):
                continue
            value = row[id_key]
            if value in seen:
                failures.append(
                    f"provenance ledger INVALID: {pack}: duplicate {id_key} {value}")
            seen.add(value)


def _provenance_source_ids(ledger: dict[str, object]) -> set[str]:
    """Provenance source ids."""
    ids: set[str] = set()
    sources = ledger.get("sources")
    if isinstance(sources, list):
        for row in sources:
            if isinstance(row, dict) and isinstance(row.get("source_id"), str):
                ids.add(row["source_id"])
    return ids


def _provenance_overlay_roots(ledger: dict[str, object], pack_root: str,
                              failures: list[str], pack: str) -> list[str]:
    """Provenance overlay roots."""
    roots: list[str] = []
    overlays = ledger.get("overlays")
    if not isinstance(overlays, list):
        return roots
    for row in overlays:
        if not isinstance(row, dict):
            continue
        root = row.get("root")
        if not isinstance(root, str):
            continue
        if not _path_inside_pack(pack_root, root):
            failures.append(
                f"provenance ledger INVALID: {pack}: overlay {row.get('overlay_id')} "
                "root escapes pack root")
        else:
            roots.append(root)
    return roots


def _path_under_root(root: str, candidate: str) -> bool:
    """Path under root."""
    return (_norm_manifest_path(root) == _norm_manifest_path(candidate)
            or _path_is_parent(root, candidate))


def _check_provenance_content_safety(ledger: dict[str, object], failures: list[str],
                                     pack: str) -> None:
    """Check provenance content safety."""
    safety = ledger.get("content_safety")
    if not isinstance(safety, dict):
        return
    for flag in CONTENT_SAFETY_FLAGS:
        if safety.get(flag) is not True:
            failures.append(
                f"provenance ledger INVALID: {pack}: content_safety.{flag} must be "
                "true (policy is exclusion of real sensitive content)")


def _check_provenance_review_gates(ledger: dict[str, object], failures: list[str],
                                   pack: str) -> None:
    """Check provenance review gates."""
    review = ledger.get("review")
    if not isinstance(review, dict):
        return
    gates = review.get("gates")
    present: set[str] = set()
    if isinstance(gates, list):
        for gate in gates:
            if isinstance(gate, dict) and isinstance(gate.get("gate_id"), str):
                present.add(gate["gate_id"])
    for required_gate in REQUIRED_REVIEW_GATES:
        if required_gate not in present:
            failures.append(
                f"provenance ledger INVALID: {pack}: review.gates missing required "
                f"gate {required_gate}")


def _check_provenance_sources(ledger: dict[str, object], failures: list[str],
                              pack: str) -> None:
    """Check provenance sources."""
    sources = ledger.get("sources")
    if not isinstance(sources, list):
        return
    for row in sources:
        if not isinstance(row, dict):
            continue
        if row.get("attribution_required") is True and not row.get("attribution"):
            failures.append(
                f"provenance ledger INVALID: {pack}: source {row.get('source_id')} "
                "sets attribution_required but carries no attribution text")


def _check_artifact_path(pack_root: str, aid: object, apath: str,
                         failures: list[str], pack: str) -> None:
    """Check artifact path."""
    if not _path_inside_pack(pack_root, apath):
        failures.append(
            f"provenance ledger INVALID: {pack}: artifact {aid} path escapes "
            "pack root")
    elif not os.path.exists(os.path.join(pack_root, apath)):
        failures.append(
            f"provenance ledger INVALID: {pack}: artifact {aid} references "
            f"missing path {apath}")


def _check_artifact_source_refs(aid: object, refs: object, source_ids: set[str],
                                failures: list[str], pack: str) -> None:
    """Check artifact source refs."""
    if not isinstance(refs, list):
        return
    for sid in refs:
        if isinstance(sid, str) and sid not in source_ids:
            failures.append(
                f"provenance ledger INVALID: {pack}: artifact {aid} "
                f"references unknown source_id {sid}")


def _artifact_under_overlay(apath: object, overlay_roots: list[str]) -> bool:
    """Artifact under overlay."""
    return isinstance(apath, str) and any(
        _path_under_root(root, apath) for root in overlay_roots)


def _check_overlay_base_overlap(overlay_roots: list[str], base_paths: list[str],
                                failures: list[str], pack: str) -> None:
    # A customer overlay must be removable without touching base content: its root
    # may not contain — or live inside — any base (non-customer) artifact root.
    """Check overlay base overlap."""
    for root in overlay_roots:
        for base in base_paths:
            if _path_under_root(root, base) or _path_under_root(base, root):
                failures.append(
                    f"provenance ledger INVALID: {pack}: overlay root {root} overlaps "
                    f"base artifact path {base}")


def _check_provenance_artifacts(ledger: dict[str, object], pack_root: str,
                                source_ids: set[str], overlay_roots: list[str],
                                failures: list[str], pack: str) -> None:
    """Check provenance artifacts."""
    artifacts = ledger.get("artifacts")
    if not isinstance(artifacts, list):
        return
    base_paths: list[str] = []
    for row in artifacts:
        if not isinstance(row, dict):
            continue
        aid = row.get("artifact_id")
        apath = row.get("path")
        if isinstance(apath, str):
            _check_artifact_path(pack_root, aid, apath, failures, pack)
        _check_artifact_source_refs(aid, row.get("sources"), source_ids, failures, pack)
        if row.get("classification") == "customer-specific":
            if not _artifact_under_overlay(apath, overlay_roots):
                failures.append(
                    f"provenance ledger INVALID: {pack}: artifact {aid} is "
                    "customer-specific but not under a declared overlay root")
        elif isinstance(apath, str):
            base_paths.append(apath)
    _check_overlay_base_overlap(overlay_roots, base_paths, failures, pack)


def _validate_provenance_ledger(pack: str, pack_yaml: dict[str, object],
                                failures: list[str]) -> None:
    """Validate provenance ledger."""
    pack_root = os.path.join(SCEN, pack)
    loaded = _load_pack_doc(pack, pack_yaml, "provenance_ledger",
                            "provenance ledger", provenance_schema_path(),
                            failures, required=True)
    if loaded is None:
        return
    schema, ledger, ledger_rel = loaded

    errors: list[str] = []
    _validate_json_schema_subset(ledger, schema, schema, "$", errors)
    for error in errors:
        failures.append(
            f"provenance ledger INVALID: scenarios/{pack}/{ledger_rel}: {error}")

    ledger_name = _get_nested(ledger, "pack.name")
    pack_name = pack_yaml.get("name")
    if ledger_name != pack_name:
        failures.append(
            f"provenance ledger INVALID: {pack}: pack name mismatch "
            f"{PACK_MANIFEST_FILE}={pack_name!r} ledger={ledger_name!r}")

    _check_provenance_duplicate_ids(ledger, failures, pack)
    _check_provenance_content_safety(ledger, failures, pack)
    _check_provenance_review_gates(ledger, failures, pack)
    _check_provenance_sources(ledger, failures, pack)
    source_ids = _provenance_source_ids(ledger)
    overlay_roots = _provenance_overlay_roots(ledger, pack_root, failures, pack)
    _check_provenance_artifacts(ledger, pack_root, source_ids, overlay_roots,
                                failures, pack)


def check_provenance_schema_example(failures: list[str]) -> None:
    """Check provenance schema example."""
    schema = _load_yaml(provenance_schema_path(), failures, "provenance schema")
    example = _load_yaml(provenance_example_path(), failures, "provenance example")
    if not isinstance(schema, dict) or not isinstance(example, dict):
        failures.append("provenance example INVALID: schema or example is not an object")
        return
    errors: list[str] = []
    _validate_json_schema_subset(example, schema, schema, "$", errors)
    for error in errors:
        failures.append(
            f"provenance example INVALID: {PROVENANCE_EXAMPLE_FILE}: {error}")
    if not errors:
        print("  [ok] _template/docs/provenance-ledger.example.yaml")


def check_provenance(failures: list[str]) -> None:
    """Check provenance."""
    check_provenance_schema_example(failures)
    for pack in _packs():
        pack_yaml_path = os.path.join(SCEN, pack, PACK_MANIFEST_FILE)
        if not os.path.isfile(pack_yaml_path):
            # check_manifest already reports the missing pack manifest
            continue
        pack_yaml = _load_yaml(pack_yaml_path, failures, "manifest")
        if not isinstance(pack_yaml, dict):
            continue
        _validate_provenance_ledger(pack, pack_yaml, failures)
        print(f"  [ok] {pack}/{PACK_MANIFEST_FILE} provenance")


def check_golden_checklist(failures: list[str]) -> None:
    """Check golden checklist."""
    for pack in _packs():
        checklist = os.path.join(SCEN, pack, "docs", "golden-readiness-checklist.md")
        if not os.path.isfile(checklist):
            failures.append(
                f"golden checklist MISSING: scenarios/{pack}/docs/"
                "golden-readiness-checklist.md")
            continue
        with open(checklist, "r", encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        required = [
            "Golden Definition Of Done",
            "Final Manual Participant Walkthrough Protocol",
            "- [ ]",
        ]
        missing = [term for term in required if term not in body]
        if missing:
            failures.append(
                f"golden checklist INCOMPLETE: scenarios/{pack}/docs/"
                f"golden-readiness-checklist.md missing {', '.join(missing)}")
        else:
            print(f"  [ok] {pack}/docs/golden-readiness-checklist.md")


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    global _REPO, SCEN
    import argparse
    parser = argparse.ArgumentParser(
        description="Validate a scenario-pack catalog against the ACES pack contract.")
    parser.add_argument(
        "--repo", default=_REPO,
        help="Catalog root containing scenarios/<pack>/ (default: current directory).")
    args = parser.parse_args(argv)
    _REPO = os.path.abspath(args.repo)
    SCEN = os.path.join(_REPO, "scenarios")

    failures: list[str] = []
    print("== shared oracle model ==")
    check_shared_oracle_model(failures)
    print("== validators ==")
    check_validators(failures)
    print("== test suites ==")
    check_tests(failures)
    print("== visibility scan ==")
    check_visibility(failures)
    print("== pack drift scan ==")
    check_wizard_spider_pack_drift(failures)
    print("== manifests ==")
    check_manifest(failures)
    print("== provenance ledgers ==")
    check_provenance(failures)
    print("== golden readiness checklists ==")
    check_golden_checklist(failures)
    print()
    if failures:
        print(f"SCENARIO-CONTENT CI: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(" - " + f)
        return 1
    print("SCENARIO-CONTENT CI: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
