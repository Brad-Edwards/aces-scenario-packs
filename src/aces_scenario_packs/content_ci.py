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
  3. **Visibility / leak scan** — no restricted operator token (``S-*`` states,
     ``<n>.<L>`` step ids, ATT&CK technique ids, ``S1.*``/``S2.*`` source
     labels) appears in any participant-facing surface (``assets/content/**``,
     ``assets/briefing/**``). This is *"the single most important invariant of
     the pack"* (scenario-design.md) — leaked operator action ordering hands
     participants the solution.
  4. **Manifest** — every pack ships a ``pack.yaml``.
  5. **Golden checklist** — every pack carries
     ``docs/golden-readiness-checklist.md`` so final manual participant review
     is planned and auditable.
  6. **Anti-extension guard** — the compatibility schema, the bundled
     template/example, and every pack carry zero extensions to ACES semantics:
     no ``scoring`` / ``validation_oracle`` / ``telemetry`` / ``lifecycle``
     manifest layer and no ``sdl/`` semantic ledger reintroduces an ACES/runtime
     concept (ADR 0009, issue #83).
  7. **SDL through ACES** — every pack's ``sdl/*.sdl.yaml`` start state parses
     and validates through ACES (``aces_sdl.parse_sdl_file``), and every
     ``flags/placement.yaml`` host resolves to a real ``Scenario.nodes`` id.
     SDL is validated *through ACES*, with no SDL schema restated here; the gate
     is fail-closed on a missing/invalid document (ADR 0011, issue #84).

Stdlib + PyYAML, plus ACES (``aces-sdl``, exactly pinned per ADR 0011) for SDL
validation. Run locally exactly as CI does:

    aces-pack-validate --repo .
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence

import yaml

from aces_scenario_packs.validation import (
    CONTENT_SAFETY_FLAGS as _SHARED_CONTENT_SAFETY_FLAGS,
    _schema_violations,
    _validate_pack_for_author_ci,
)

CONTENT_SAFETY_FLAGS = _SHARED_CONTENT_SAFETY_FLAGS

# Canonical contract resources ship inside this installed package (schemas,
# and template). They are resolved relative to the package,
# never the consumer's working tree.
_PKG = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_PKG, "resources")
_SCHEMAS_DIR = os.path.join(_RES, "schemas")
_TEMPLATE_DIR = os.path.join(_RES, "template")

# The catalog under validation is the consumer's tree: <_REPO>/scenarios/<pack>/.
# Defaults to the current directory; override with --repo, or by setting these
# module globals directly (tests do this).
_REPO = os.getcwd()
SCEN = os.path.join(_REPO, "scenarios")

COMPATIBILITY_MANIFEST_FILE = "pack.compatibility.yaml"
# Human-readable label used in failure messages for the compatibility manifest.
COMPATIBILITY_MANIFEST_LABEL = "compatibility manifest"
PACK_MANIFEST_FILE = "pack.yaml"
COMPATIBILITY_SCHEMA_FILE = "pack-compatibility.schema.yaml"
PROVENANCE_SCHEMA_FILE = "provenance.schema.yaml"
# Display labels for the packaged example fixtures (used in messages only).
COMPATIBILITY_EXAMPLE_FILE = os.path.join("template", "pack.compatibility.example.yaml")
PROVENANCE_EXAMPLE_FILE = os.path.join("template", "docs", "provenance-ledger.example.yaml")
# Safety attestations that must all be true to ship — the policy is EXCLUSION of
# real sensitive content, never a weaker classification.
# Publication-review gates the ledger must cover (acceptance criterion: a review
# checklist covering licensing, attribution, sensitive data, and offensive
# tooling boundaries). `customer-overlay` is an optional extra gate.

# Anti-extension guard vocabulary (issue #83). This repository defines ZERO
# extensions to ACES semantics (ADR 0009): scoring, validation-oracle, telemetry,
# and lifecycle (reset/rebuild/teardown) are ACES/runtime concerns, so they are
# not compatibility-manifest layers, and the pack-local semantic ledgers that
# projected them do not belong in `sdl/` (which holds ACES SDL documents only).
# These frozensets are the single source of truth the guard reads. They are named
# constants — not inline literals — so a later change (#84/#86) can swap in the
# ACES contract corpus as the authority without rewriting the gate. The guard is
# structural: it inspects declared schema properties and manifest keys, never free
# prose, so docs that name a removed concept to reject or defer it never trip it.
FORBIDDEN_MANIFEST_LAYERS = frozenset(
    {"scoring", "validation_oracle", "telemetry", "lifecycle"})
FORBIDDEN_SDL_LEDGERS = frozenset({"scoring.yaml", "telemetry.yaml", "objectives.yaml"})


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

class _AuthorStaticView(object):
    """One shared per-pack static-validation snapshot for author-CI adapters."""

    __slots__ = (
        "global_failures",
        "manifest_failures",
        "provenance_failures",
        "sdl_failures",
        "scenarios",
    )

    def __init__(
        self,
        global_failures: tuple[str, ...],
        manifest_failures: tuple[str, ...],
        provenance_failures: tuple[str, ...],
        sdl_failures: tuple[str, ...],
        scenarios: tuple[object, ...],
    ) -> None:
        self.global_failures = global_failures
        self.manifest_failures = manifest_failures
        self.provenance_failures = provenance_failures
        self.sdl_failures = sdl_failures
        self.scenarios = scenarios

    @property
    def ok(self) -> bool:
        """Whether the candidate passed the complete shared static contract."""
        return not any((
            self.global_failures,
            self.manifest_failures,
            self.provenance_failures,
            self.sdl_failures,
        ))


_AUTHOR_STATIC_CACHE: dict[str, _AuthorStaticView] = {}

# Operator tokens that must never reach participant-facing surfaces.
TOKEN_PATTERNS = [
    (re.compile(r"\bS-[A-Z]{3,}\b"), "restricted S-* state"),
    (re.compile(r"\bS[12]\.\d{1,2}\b"), "source label S1.*/S2.*"),
    (re.compile(r"\bT\d{4}(?:\.\d{3})?\b"), "ATT&CK technique id"),
    (re.compile(r"(?<![\w.])(?:10|[1-9])\.[A-Z](?![\w])"), "attack-path step id"),
]
PARTICIPANT_DIRS = [
    ("assets", "content"),
    ("assets", "briefing"),
    ("challenges",),
]
TEXT_EXT = {".md", ".txt", ".yaml", ".yml", ".csv", ".json", ".log", ".note"}


def _discovery_failure(failures: list[str] | None, location: str) -> None:
    """Record a bounded discovery failure, or raise for an unwrapped caller."""
    message = f"CATALOG DISCOVERY FAILED: {location} could not be inspected"
    if failures is None:
        raise RuntimeError(message)
    failures.append(message)


def _packs(
    scenarios_root: str | None = None,
    failures: list[str] | None = None,
) -> tuple[str, ...]:
    """Return one sorted snapshot of direct manifest-bearing pack directories."""
    root = os.path.abspath(scenarios_root or SCEN)
    try:
        with os.scandir(root) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
    except FileNotFoundError:
        return ()
    except OSError:
        _discovery_failure(failures, "scenarios/")
        return ()

    packs: list[str] = []
    for entry in children:
        try:
            if not entry.is_dir(follow_symlinks=False):
                continue
            with os.scandir(entry.path) as pack_entries:
                has_marker = any(
                    child.name == PACK_MANIFEST_FILE for child in pack_entries
                )
        except OSError:
            _discovery_failure(failures, "scenarios/<entry>/")
            continue
        if has_marker:
            packs.append(entry.name)
    return tuple(packs)


# Directories under a pack that ship static `validate_*.py validate` gates. The
# sdl ledgers (#21–#24) and the delivery-profile bundles (#50) both ship one.
VALIDATOR_DIRS = ("sdl", "profiles")

# SDL-through-ACES gate (#84, ADR 0011). Every pack's start state lives under
# `sdl/` as one or more `*.sdl.yaml` documents authored in ACES SDL; the
# placement map's `host` join points at a node in that start state.
SDL_DIR = "sdl"
SDL_DOC_SUFFIX = ".sdl.yaml"
PLACEMENT_REL = os.path.join("flags", "placement.yaml")


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


def check_validators(
    failures: list[str],
    packs: Sequence[str] | None = None,
) -> None:
    """Check validators."""
    for pack in packs if packs is not None else _packs():
        for sub in VALIDATOR_DIRS:
            _check_validator_dir(pack, sub, failures)


def check_tests(
    failures: list[str],
    packs: Sequence[str] | None = None,
) -> None:
    """Check tests."""
    for pack in packs if packs is not None else _packs():
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


def _load_aces_sdl() -> tuple[Callable[..., object], type[BaseException]]:
    """Return ``(parse_sdl_file, SDLError)`` from ACES, or raise ``ImportError``.

    ``aces-sdl`` is a hard, exactly-pinned dependency (ADR 0011): SDL is
    validated *through ACES*, never a local restatement. The import is isolated
    (and lazy) so a broken environment where the pinned dep is missing surfaces
    as a fail-closed gate failure in :func:`check_sdl` rather than crashing the
    import of the other, ACES-independent gates.
    """
    from aces_sdl import SDLError, parse_sdl_file
    return parse_sdl_file, SDLError


def _sdl_docs(pack: str) -> list[str]:
    """Direct ``sdl/*.sdl.yaml`` documents for a pack (sorted, non-recursive)."""
    sdl_dir = os.path.join(SCEN, pack, SDL_DIR)
    if not os.path.isdir(sdl_dir):
        return []
    return [
        os.path.join(sdl_dir, name)
        for name in sorted(os.listdir(sdl_dir))
        if name.endswith(SDL_DOC_SUFFIX)
        and os.path.isfile(os.path.join(sdl_dir, name))
    ]


def _sdl_node_ids(scenario: object) -> set[str]:
    """Node ids declared by a parsed ACES ``Scenario`` (the ``nodes.<id>`` keys).

    Reads the ACES-owned ``Scenario.nodes`` mapping directly; it never reloads or
    reinterprets the SDL. Isolated so the placement cross-check is unit-testable
    against a lightweight stand-in scenario.
    """
    return set(getattr(scenario, "nodes", {}) or {})


def _author_provenance_failure(pack: str, code: str, detail: str) -> str:
    """Render one shared provenance code for author CI."""

    if code == "provenance.pointer.missing":
        failure = (
            f"provenance ledger MISSING: scenarios/{pack}/{PACK_MANIFEST_FILE} "
            "has no provenance_ledger pointer"
        )
    elif code == "provenance.pointer.invalid":
        failure = (
            f"provenance ledger INVALID: {pack}: provenance_ledger path "
            "escapes pack root"
        )
    elif code == "provenance.missing":
        failure = f"provenance ledger MISSING: scenarios/{pack}/{detail}"
    elif code == "provenance.name-mismatch":
        failure = f"provenance ledger INVALID: {pack}: pack name mismatch"
    elif code == "provenance.safety.required":
        field = detail.rsplit(":", 1)[-1]
        failure = f"provenance ledger INVALID: {pack}: {field} must be true"
    elif code == "provenance.review-gate.missing":
        gate = detail.rsplit(".", 1)[-1]
        failure = (
            f"provenance ledger INVALID: {pack}: review.gates missing required "
            f"gate {gate}"
        )
    else:
        failure = f"provenance ledger INVALID: scenarios/{pack}/{detail}: {code}"
    return failure


def _partition_author_static_error(
    pack: str,
    error: str,
    global_failures: list[str],
    manifest_failures: list[str],
    provenance_failures: list[str],
    sdl_failures: list[str],
) -> None:
    """Partition one shared error exactly once for the author-CI presentation."""

    code, _, detail = error.partition(": ")
    if code == "sdl.missing":
        sdl_failures.append(
            f"SDL MISSING: scenarios/{pack}/{SDL_DIR} has no *{SDL_DOC_SUFFIX} "
            "start-state document (every pack requires an SDL start state)"
        )
    elif code.startswith("sdl."):
        sdl_failures.append(f"SDL INVALID: scenarios/{pack}/{detail}: {code}")
    elif code.startswith("provenance.") or detail.startswith(
        "docs/provenance-ledger.yaml"
    ):
        provenance_failures.append(_author_provenance_failure(pack, code, detail))
    elif code.startswith(("pack.", "compatibility.")) or detail.startswith(
        ("pack.yaml", "pack.compatibility.yaml")
    ):
        manifest_failures.append(
            f"compatibility manifest INVALID: scenarios/{pack}/{detail}: {code}"
        )
    elif code.startswith("challenges."):
        global_failures.append(
            f"CHALLENGE INVALID: scenarios/{pack}/{detail}: {code}"
        )
    else:
        global_failures.append(f"PACK STATIC INVALID: scenarios/{pack}: {code}")


def _author_static_view(pack: str) -> _AuthorStaticView:
    """Return the sole static-validation snapshot for one pack in this run."""

    pack_root = os.path.abspath(os.path.join(SCEN, pack))
    cached = _AUTHOR_STATIC_CACHE.get(pack_root)
    if cached is not None:
        return cached
    result, scenarios = _validate_pack_for_author_ci(pack_root)
    global_failures: list[str] = []
    manifest_failures: list[str] = []
    provenance_failures: list[str] = []
    sdl_failures: list[str] = []
    for error in result.errors:
        _partition_author_static_error(
            pack,
            error,
            global_failures,
            manifest_failures,
            provenance_failures,
            sdl_failures,
        )
    view = _AuthorStaticView(
        tuple(global_failures),
        tuple(manifest_failures),
        tuple(provenance_failures),
        tuple(sdl_failures),
        scenarios,
    )
    _AUTHOR_STATIC_CACHE[pack_root] = view
    return view


def check_static_contract(
    failures: list[str],
    packs: Sequence[str] | None = None,
) -> dict[str, _AuthorStaticView]:
    """Validate and report every pack's shared static contract exactly once."""

    views: dict[str, _AuthorStaticView] = {}
    for pack in packs if packs is not None else _packs():
        view = _author_static_view(pack)
        views[pack] = view
        failures.extend(view.global_failures)
        failures.extend(view.manifest_failures)
        failures.extend(view.provenance_failures)
        failures.extend(view.sdl_failures)
    return views


def _iter_placement_hosts(pack: str, failures: list[str]) -> Iterator[str]:
    """Yield each declared ``flags/placement.yaml.flags[].host`` for a pack.

    Only the canonical structured reference (``flags[].host``) is read; no host
    is inferred from prose, filenames, or arbitrary keys (ADR 0011). A malformed
    placement document is reported and yields nothing.
    """
    placement_path = os.path.join(SCEN, pack, PLACEMENT_REL)
    if not os.path.isfile(placement_path):
        return
    doc = _load_yaml(placement_path, failures, "placement map")
    flags = doc.get("flags") if isinstance(doc, dict) else None
    if not isinstance(flags, list):
        return
    for row in flags:
        if isinstance(row, dict) and isinstance(row.get("host"), str):
            yield row["host"]


def _check_pack_sdl(
    pack: str,
    failures: list[str],
    static_view: _AuthorStaticView | None = None,
) -> None:
    """Delegate static SDL validation, then perform the author-only placement join."""
    report_static = static_view is None
    view = static_view or _author_static_view(pack)
    if report_static:
        failures.extend(view.sdl_failures)

    node_ids: set[str] = set()
    for scenario in view.scenarios:
        node_ids |= _sdl_node_ids(scenario)
    if view.scenarios:
        print(f"  [ok] {pack} SDL documents ({len(view.scenarios)})")

    # Only join placement hosts when at least one variant validated; otherwise
    # the SDL failure above is the actionable one and the node set is unknown.
    if not view.scenarios:
        return
    for host in _iter_placement_hosts(pack, failures):
        if host not in node_ids:
            failures.append(
                f"FLAG PLACEMENT INVALID: scenarios/{pack}/{PLACEMENT_REL}: "
                f"host {host!r} does not resolve to an SDL start-state node")


def check_sdl(
    failures: list[str],
    static_views: dict[str, _AuthorStaticView] | None = None,
    packs: Sequence[str] | None = None,
) -> None:
    """Validate every pack's ``sdl/`` through ACES and cross-check flag placement.

    ADR 0011: SDL is validated *through ACES* (``parse_sdl_file`` with full
    semantic validation), with no SDL schema restated here. The gate is
    fail-closed — a pack with no start-state document, a document ACES rejects,
    a placement ``host`` that resolves to no node, or a missing pinned ``aces-sdl``
    dependency all fail.
    """
    try:
        _load_aces_sdl()
    except ImportError as exc:
        failures.append(
            "SDL VALIDATION UNAVAILABLE: aces-sdl (pinned dependency, ADR 0011) "
            f"is not importable: {exc}")
        return
    for pack in packs if packs is not None else _packs():
        _check_pack_sdl(
            pack,
            failures,
            static_views.get(pack) if static_views is not None else None,
        )


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
    vocabularies (restricted ``S-*`` states, ATT&CK technique ids, step ids) are
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
    legitimately cite restricted operator material. New bundles are covered
    automatically.
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


def check_visibility(
    failures: list[str],
    packs: Sequence[str] | None = None,
) -> None:
    """Check visibility."""
    for pack in packs if packs is not None else _packs():
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


def _load_yaml(path: str, failures: list[str], label: str) -> object:
    """Load yaml."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        failures.append(f"{label} INVALID: {path}: {exc}")
        return None


def _schema_properties(schema: dict[str, object]) -> dict[str, object]:
    """Schema properties."""
    props = schema.get("properties", {})
    return props if isinstance(props, dict) else {}


def _validate_json_schema_subset(value: object, schema: dict[str, object],
                                 root_schema: dict[str, object], path: str,
                                 errors: list[str]) -> None:
    """Render the shared pack-schema validator for author-CI diagnostics."""
    for violation in _schema_violations(value, schema, root_schema, path):
        descriptions = {
            "required": "required field missing",
            "unknown": "unknown field",
            "type": "unexpected type",
            "const": "unexpected constant",
            "enum": "unsupported value",
            "pattern": "does not match required pattern",
            "min-items": "too few items",
            "ref": "unresolved schema ref",
        }
        errors.append(f"{violation.path}: {descriptions.get(violation.code, 'invalid')}")


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


def _referenced_compatibility_manifest(
    pack_root: str,
    pack_yaml: dict[str, object],
    failures: list[str],
) -> dict[str, object] | None:
    """Load a contained, existing compatibility manifest for author joins."""

    manifest: dict[str, object] | None = None
    rel = pack_yaml.get("compatibility_manifest")
    if isinstance(rel, str) and _path_inside_pack(pack_root, rel):
        manifest_path = os.path.join(pack_root, rel)
        if os.path.isfile(manifest_path):
            loaded = _load_yaml(
                manifest_path, failures, COMPATIBILITY_MANIFEST_LABEL
            )
            if isinstance(loaded, dict):
                manifest = loaded
    return manifest


def _validate_compatibility_manifest(
    pack: str,
    pack_yaml: dict[str, object],
    failures: list[str],
    static_view: _AuthorStaticView | None = None,
) -> None:
    """Delegate compatibility shape checks, then run author-only deep joins."""
    pack_root = os.path.join(SCEN, pack)
    report_static = static_view is None
    view = static_view or _author_static_view(pack)
    if report_static:
        failures.extend(view.manifest_failures)

    manifest = _referenced_compatibility_manifest(pack_root, pack_yaml, failures)
    if manifest is None:
        return

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


def check_manifest(
    failures: list[str],
    static_views: dict[str, _AuthorStaticView] | None = None,
    packs: Sequence[str] | None = None,
) -> None:
    """Check manifest."""
    check_compatibility_schema_example(failures)
    for pack in packs if packs is not None else _packs():
        pack_yaml_path = os.path.join(SCEN, pack, PACK_MANIFEST_FILE)
        if not os.path.isfile(pack_yaml_path):
            failures.append(f"manifest MISSING: scenarios/{pack}/{PACK_MANIFEST_FILE}")
            continue
        pack_yaml = _load_yaml(pack_yaml_path, failures, "manifest")
        if not isinstance(pack_yaml, dict):
            failures.append(f"manifest INVALID: scenarios/{pack}/{PACK_MANIFEST_FILE}")
            continue
        _validate_compatibility_manifest(
            pack,
            pack_yaml,
            failures,
            static_views.get(pack) if static_views is not None else None,
        )
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
                                failures: list[str],
                                static_view: _AuthorStaticView | None = None) -> None:
    """Delegate static provenance checks, then run author-only relational joins."""
    pack_root = os.path.join(SCEN, pack)
    report_static = static_view is None
    view = static_view or _author_static_view(pack)
    if report_static:
        failures.extend(view.provenance_failures)

    rel = pack_yaml.get("provenance_ledger")
    if not isinstance(rel, str) or not _path_inside_pack(pack_root, rel):
        return
    ledger_path = os.path.join(pack_root, rel)
    if not os.path.isfile(ledger_path):
        return
    ledger = _load_yaml(ledger_path, failures, "provenance ledger")
    if not isinstance(ledger, dict):
        return

    _check_provenance_duplicate_ids(ledger, failures, pack)
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


def check_provenance(
    failures: list[str],
    static_views: dict[str, _AuthorStaticView] | None = None,
    packs: Sequence[str] | None = None,
) -> None:
    """Check provenance."""
    check_provenance_schema_example(failures)
    for pack in packs if packs is not None else _packs():
        pack_yaml_path = os.path.join(SCEN, pack, PACK_MANIFEST_FILE)
        if not os.path.isfile(pack_yaml_path):
            # check_manifest already reports the missing pack manifest
            continue
        pack_yaml = _load_yaml(pack_yaml_path, failures, "manifest")
        if not isinstance(pack_yaml, dict):
            continue
        _validate_provenance_ledger(
            pack,
            pack_yaml,
            failures,
            static_views.get(pack) if static_views is not None else None,
        )
        print(f"  [ok] {pack}/{PACK_MANIFEST_FILE} provenance")


def check_golden_checklist(
    failures: list[str],
    packs: Sequence[str] | None = None,
) -> None:
    """Check golden checklist."""
    for pack in packs if packs is not None else _packs():
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


def _forbidden_manifest_keys(manifest: object) -> list[str]:
    """Sorted forbidden-layer keys present at the top level of a manifest dict."""
    if not isinstance(manifest, dict):
        return []
    return sorted(key for key in manifest if key in FORBIDDEN_MANIFEST_LAYERS)


def _check_schema_no_extension_layers(failures: list[str]) -> None:
    """The packaged compatibility schema must declare no forbidden layer.

    Structural check: a forbidden concept is a *declared property* of the schema,
    not a word in its description. This is the durable enforcement that the schema
    itself cannot silently reintroduce a removed ACES-semantic layer.
    """
    schema = _load_yaml(compatibility_schema_path(), failures, "compatibility schema")
    if not isinstance(schema, dict):
        return
    for key in sorted(k for k in _schema_properties(schema)
                      if k in FORBIDDEN_MANIFEST_LAYERS):
        failures.append(
            f"ANTI-EXTENSION: {COMPATIBILITY_SCHEMA_FILE} declares forbidden "
            f"ACES-semantic layer {key!r} as a manifest property; scoring/"
            "validation_oracle/telemetry/lifecycle are ACES concerns (ADR 0009)")


def _check_packaged_manifest_no_extension_layers(failures: list[str]) -> None:
    """The bundled template + example manifests must carry no forbidden layer."""
    for path, label in (
        (compatibility_example_path(), COMPATIBILITY_EXAMPLE_FILE),
        (os.path.join(_TEMPLATE_DIR, COMPATIBILITY_MANIFEST_FILE),
         os.path.join("template", COMPATIBILITY_MANIFEST_FILE)),
    ):
        if not os.path.isfile(path):
            continue
        manifest = _load_yaml(path, failures, COMPATIBILITY_MANIFEST_LABEL)
        for key in _forbidden_manifest_keys(manifest):
            failures.append(
                f"ANTI-EXTENSION: {label} carries forbidden ACES-semantic layer "
                f"{key!r} (ADR 0009)")


def _check_pack_no_extension_layers(pack: str, failures: list[str]) -> None:
    """A catalog pack must not reintroduce a removed layer or `sdl/` ledger."""
    pack_root = os.path.join(SCEN, pack)
    pack_yaml_path = os.path.join(pack_root, PACK_MANIFEST_FILE)
    pack_yaml = (_load_yaml(pack_yaml_path, failures, "manifest")
                 if os.path.isfile(pack_yaml_path) else None)
    if isinstance(pack_yaml, dict):
        rel = pack_yaml.get("compatibility_manifest")
        if isinstance(rel, str) and _path_inside_pack(pack_root, rel):
            manifest_path = os.path.join(pack_root, rel)
            if os.path.isfile(manifest_path):
                manifest = _load_yaml(manifest_path, failures, COMPATIBILITY_MANIFEST_LABEL)
                for key in _forbidden_manifest_keys(manifest):
                    failures.append(
                        f"ANTI-EXTENSION: scenarios/{pack}/{rel} carries forbidden "
                        f"ACES-semantic layer {key!r} (ADR 0009)")
    sdl_dir = os.path.join(pack_root, "sdl")
    for ledger in sorted(FORBIDDEN_SDL_LEDGERS):
        if os.path.isfile(os.path.join(sdl_dir, ledger)):
            failures.append(
                f"ANTI-EXTENSION: scenarios/{pack}/sdl/{ledger} is a removed "
                "ACES-semantic ledger; sdl/ holds ACES SDL documents only (ADR 0009)")


def check_anti_extension(
    failures: list[str],
    packs: Sequence[str] | None = None,
) -> None:
    """Fail if the format or any pack reintroduces a removed ACES extension.

    ADR 0009 makes this repository ACES-subordinate with zero extensions to ACES
    semantics. This gate is the durable enforcement of that charter across the
    schema, the bundled template/example, and every catalog pack — so a removed
    scoring/validation_oracle/telemetry/lifecycle layer (or an `sdl/` semantic
    ledger) cannot silently return.
    """
    before = len(failures)
    _check_schema_no_extension_layers(failures)
    _check_packaged_manifest_no_extension_layers(failures)
    for pack in packs if packs is not None else _packs():
        _check_pack_no_extension_layers(pack, failures)
    if len(failures) == before:
        print(f"  [ok] anti-extension guard ({len(FORBIDDEN_MANIFEST_LAYERS)} "
              f"forbidden layers, {len(FORBIDDEN_SDL_LEDGERS)} forbidden sdl ledgers)")


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
    _AUTHOR_STATIC_CACHE.clear()

    failures: list[str] = []
    packs = _packs(SCEN, failures)
    print("== static pack contract ==")
    static_views = check_static_contract(failures, packs)
    runnable_packs = tuple(
        pack for pack in packs
        if (view := static_views.get(pack)) is not None and view.ok
    )
    print("== validators ==")
    check_validators(failures, runnable_packs)
    print("== test suites ==")
    check_tests(failures, runnable_packs)
    print("== sdl (ACES) ==")
    check_sdl(failures, static_views, packs)
    print("== visibility scan ==")
    check_visibility(failures, packs)
    print("== manifests ==")
    check_manifest(failures, static_views, packs)
    print("== anti-extension guard ==")
    check_anti_extension(failures, packs)
    print("== provenance ledgers ==")
    check_provenance(failures, static_views, packs)
    print("== golden readiness checklists ==")
    check_golden_checklist(failures, packs)
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
