#!/usr/bin/env python3
"""Reusable validation-oracle model for ACES scenario packs.

This module validates shared oracle source artifacts. It is intentionally a
static, read-only contract: it checks parsed committed YAML shape and
cross-references, and renders bounded exports for operators or benchmark
consumers. It does not read live ranges, write scores, call CTFd, or mutate
scenario state.
"""

from __future__ import annotations

import os
import re
from typing import Any


SCHEMA_VERSION = 1

MUST_BE_STRING = "must be a string"
PREDICATE_REQUIRED = "predicate is required"
REFERENCE_UNKNOWN = "reference is unknown"

TOP_LEVEL_KEYS = {
    "schema_version",
    "oracle_id",
    "scenario",
    "visibility",
    "validator",
    "consumers",
    "path_steps",
    "outcomes",
    "accepted_alternates",
    "exports",
}
SCENARIO_KEYS = {"id", "title"}
VISIBILITY_KEYS = {"oracle_roots", "participant_roots"}
ROOT_KEYS = {"path", "description"}
VALIDATOR_KEYS = {"idempotent", "mutates_scenario_state", "evidence_namespace"}
CONSUMER_KEYS = {"id", "type", "description"}
STEP_KEYS = {
    "id",
    "title",
    "classification",
    "prerequisites",
    "success_state",
    "required_evidence",
    "optional_evidence",
    "failure_states",
}
EVIDENCE_KEYS = {
    "id",
    "kind",
    "predicate",
    "source",
    "proof_fields",
    "reset_owner",
    "mutates_scenario_state",
}
FAILURE_KEYS = {"id", "predicate", "severity"}
OUTCOME_KEYS = {
    "id",
    "title",
    "required",
    "success_state",
    "canonical_steps",
    "required_evidence",
    "optional_evidence",
    "failure_states",
    "awards",
}
AWARD_KEYS = {"consumer", "adapter", "points"}
ALTERNATE_KEYS = {"id", "title", "award", "predicate", "evidence", "review"}
ALTERNATE_AWARD_KEYS = {"outcome", "points"}
REVIEW_KEYS = {"status", "rationale"}
EXPORT_KEYS = {"id", "audience", "visibility", "includes"}

CONSUMER_TYPES = frozenset({"native", "ctfd", "agent_benchmark", "operator_debrief"})
STEP_CLASSES = frozenset({"canonical", "optional", "telemetry_only"})
EVIDENCE_KINDS = frozenset({
    "authentication",
    "collection",
    "credential_access",
    "exfil",
    "identity_workflow",
    "impact",
    "objective_stage",
    "process_creation",
    "recovery",
    "service_creation",
})
FAILURE_SEVERITIES = frozenset({"blocking", "warning"})
EXPORT_AUDIENCES = frozenset({"operator_debrief", "agent_benchmark"})
EXPORT_VISIBILITIES = {
    "operator_debrief": "operator_only",
    "agent_benchmark": "participant_safe",
}
SAFE_PROOF_FIELDS = frozenset({
    "actor",
    "actor_role",
    "asset",
    "asset_id",
    "byte_count",
    "destination",
    "digest",
    "event_kind",
    "factor_id",
    "object_id",
    "outcome_id",
    "participant",
    "protocol",
    "range_instance",
    "record_count",
    "session_id_digest",
    "source_hook",
    "stage",
    "status",
    "timestamp",
    "workflow_id",
})
REQUIRED_NAMESPACE = frozenset({"range_instance", "participant"})

_IDENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_STEP_ID_RE = re.compile(r"^\d+(?:\.[A-Z])?$")
_STATE_RE = re.compile(r"^S-[A-Z0-9]+$")


class Issue:
    """Validation issue envelope shared by the oracle model."""

    def __init__(self, object_type: str, object_id: str, field: str,
                 invariant: str, detail: str):
        """Initialize the instance."""
        self.object_type = object_type
        self.object_id = object_id
        self.field = field
        self.invariant = invariant
        self.detail = detail

    def __str__(self) -> str:
        """Return the string representation."""
        target = self.object_type
        if self.object_id:
            target += f":{self.object_id}"
        if self.field:
            target += f".{self.field}"
        return f"{target}: {self.invariant}: {self.detail}"


class OracleValidationError(Exception):
    """Raised when rendering is requested for an invalid oracle artifact."""

    def __init__(self, issues: list[Issue]):
        """Initialize the instance."""
        self.issues = issues
        super().__init__(
            f"{len(issues)} oracle validation issue(s):\n  "
            + "\n  ".join(str(issue) for issue in issues)
        )


def _unknown(issues: list[Issue], obj: Any, allowed: set[str],
             object_type: str, object_id: str) -> None:
    """Unknown."""
    if not isinstance(obj, dict):
        return
    for key in obj:
        if key not in allowed:
            issues.append(Issue(object_type, object_id, key, "unknown_field",
                                "unexpected field"))


def _require(issues: list[Issue], obj: dict[str, Any], fields: list[str],
             object_type: str, object_id: str) -> None:
    """Require."""
    for field in fields:
        if field not in obj or obj.get(field) in (None, "", []):
            issues.append(Issue(object_type, object_id, field, "required",
                                "missing or empty"))


def _as_mapping(issues: list[Issue], value: Any, object_type: str,
                object_id: str) -> dict[str, Any]:
    """As mapping."""
    if isinstance(value, dict):
        return value
    issues.append(Issue(object_type, object_id, "", "type_error",
                        "must be a mapping"))
    return {}


def _as_list(issues: list[Issue], value: Any, object_type: str,
             object_id: str, field: str) -> list[Any]:
    """As list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    issues.append(Issue(object_type, object_id, field, "type_error",
                        "must be a list"))
    return []


def _as_str_list(issues: list[Issue], value: Any, object_type: str,
                 object_id: str, field: str) -> list[str]:
    """As str list."""
    rows = _as_list(issues, value, object_type, object_id, field)
    out: list[str] = []
    for idx, item in enumerate(rows):
        if not isinstance(item, str):
            issues.append(Issue(object_type, object_id, f"{field}[{idx}]",
                                "type_error", MUST_BE_STRING))
            continue
        out.append(item)
    return out


def _valid_ident(value: Any) -> bool:
    """Valid ident."""
    return isinstance(value, str) and bool(_IDENT_RE.match(value))


def _validate_ident(issues: list[Issue], value: Any, object_type: str,
                    object_id: str, field: str) -> None:
    """Validate ident."""
    if value in (None, ""):
        return
    if not _valid_ident(value):
        issues.append(Issue(object_type, object_id, field, "ident_charset",
                            "identifier must match [A-Za-z0-9][A-Za-z0-9._-]*"))


def _require_text(issues: list[Issue], obj: dict[str, Any], object_type: str,
                  object_id: str, field: str, detail: str) -> None:
    """Require text."""
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.append(Issue(object_type, object_id, field, "required", detail))


def _record_unique(issues: list[Issue], seen: set[str], value: str,
                   object_type: str, field: str) -> None:
    """Record unique."""
    if value in seen:
        issues.append(Issue(object_type, value, field, "duplicate_id",
                            "identifier must be unique"))
    seen.add(value)


def _path_is_relative(path: str) -> bool:
    """Path is relative."""
    if not path or os.path.isabs(path) or "\\" in path:
        return False
    norm = os.path.normpath(path)
    return norm != ".." and not norm.startswith(".." + os.sep)


def _norm_path(path: str) -> str:
    """Norm path."""
    return os.path.normpath(path).replace("\\", "/").rstrip("/")


def _paths_overlap(left: str, right: str) -> bool:
    """Paths overlap."""
    a = _norm_path(left)
    b = _norm_path(right)
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def _validate_paths(issues: list[Issue], rows: list[Any], object_type: str) -> list[str]:
    """Validate paths."""
    paths: list[str] = []
    seen: set[str] = set()
    for idx, raw in enumerate(rows):
        obj = _as_mapping(issues, raw, object_type, str(idx))
        _unknown(issues, obj, ROOT_KEYS, object_type, str(idx))
        _require(issues, obj, ["path"], object_type, str(idx))
        path = obj.get("path")
        if not isinstance(path, str):
            issues.append(Issue(object_type, str(idx), "path", "type_error",
                                MUST_BE_STRING))
            continue
        if not _path_is_relative(path):
            issues.append(Issue(object_type, path, "path", "path_escape",
                                "path must stay relative to the pack root"))
            continue
        norm = _norm_path(path)
        _record_unique(issues, seen, norm, object_type, "path")
        paths.append(norm)
    return paths


def _validate_top(data: dict[str, Any], issues: list[Issue]) -> None:
    """Validate top."""
    _unknown(issues, data, TOP_LEVEL_KEYS, "oracle", "root")
    _require(issues, data, [
        "schema_version", "oracle_id", "scenario", "visibility", "validator",
        "consumers", "path_steps", "outcomes", "exports",
    ], "oracle", "root")
    if data.get("schema_version") != SCHEMA_VERSION:
        issues.append(Issue("oracle", str(data.get("oracle_id", "root")),
                            "schema_version", "schema_version",
                            "unsupported schema version"))
    _validate_ident(issues, data.get("oracle_id"), "oracle",
                    str(data.get("oracle_id", "root")), "oracle_id")


def _validate_scenario(data: dict[str, Any], issues: list[Issue]) -> None:
    """Validate scenario."""
    scenario = _as_mapping(issues, data.get("scenario"), "scenario", "")
    _unknown(issues, scenario, SCENARIO_KEYS, "scenario", str(scenario.get("id", "")))
    _require(issues, scenario, ["id", "title"], "scenario", str(scenario.get("id", "")))
    _validate_ident(issues, scenario.get("id"), "scenario",
                    str(scenario.get("id", "")), "id")
    if "title" in scenario and not isinstance(scenario.get("title"), str):
        issues.append(Issue("scenario", str(scenario.get("id", "")), "title",
                            "type_error", MUST_BE_STRING))


def _validate_visibility(data: dict[str, Any], issues: list[Issue]) -> None:
    """Validate visibility."""
    visibility = _as_mapping(issues, data.get("visibility"), "visibility", "")
    _unknown(issues, visibility, VISIBILITY_KEYS, "visibility", "")
    _require(issues, visibility, ["oracle_roots", "participant_roots"],
             "visibility", "")
    oracle_paths = _validate_paths(
        issues,
        _as_list(issues, visibility.get("oracle_roots"), "visibility", "",
                 "oracle_roots"),
        "oracle_root",
    )
    participant_paths = _validate_paths(
        issues,
        _as_list(issues, visibility.get("participant_roots"), "visibility", "",
                 "participant_roots"),
        "participant_root",
    )
    for oracle_path in oracle_paths:
        for participant_path in participant_paths:
            if _paths_overlap(oracle_path, participant_path):
                issues.append(Issue(
                    "visibility", oracle_path, "oracle_roots",
                    "visibility_overlap",
                    "oracle/private paths must not overlap participant roots",
                ))


def _validate_validator(data: dict[str, Any], issues: list[Issue]) -> None:
    """Validate validator."""
    validator = _as_mapping(issues, data.get("validator"), "validator", "")
    _unknown(issues, validator, VALIDATOR_KEYS, "validator", "")
    _require(issues, validator, ["idempotent", "mutates_scenario_state",
                                 "evidence_namespace"], "validator", "")
    if validator.get("idempotent") is not True:
        issues.append(Issue("validator", "", "idempotent",
                            "idempotent_validator",
                            "validator must be explicitly idempotent"))
    if validator.get("mutates_scenario_state") is not False:
        issues.append(Issue("validator", "", "mutates_scenario_state",
                            "idempotent_validator",
                            "validator must not mutate scenario state"))
    namespace = set(_as_str_list(issues, validator.get("evidence_namespace"),
                                 "validator", "", "evidence_namespace"))
    missing = REQUIRED_NAMESPACE - namespace
    if missing:
        issues.append(Issue("validator", "", "evidence_namespace",
                            "namespace_required",
                            "range_instance and participant are required"))


def _validate_consumers(data: dict[str, Any], issues: list[Issue]) -> set[str]:
    """Validate consumers."""
    ids: set[str] = set()
    consumer_types: set[str] = set()
    for idx, raw in enumerate(_as_list(issues, data.get("consumers"),
                                      "oracle", "root", "consumers")):
        obj = _as_mapping(issues, raw, "consumer", str(idx))
        cid = str(obj.get("id", idx))
        _unknown(issues, obj, CONSUMER_KEYS, "consumer", cid)
        _require(issues, obj, ["id", "type"], "consumer", cid)
        _validate_ident(issues, obj.get("id"), "consumer", cid, "id")
        if isinstance(obj.get("id"), str):
            _record_unique(issues, ids, obj["id"], "consumer", "id")
        ctype = obj.get("type")
        if ctype not in CONSUMER_TYPES:
            issues.append(Issue("consumer", cid, "type", "enum",
                                "unsupported consumer type"))
        elif isinstance(ctype, str):
            consumer_types.add(ctype)
    if "ctfd" in consumer_types and not (consumer_types - {"ctfd"}):
        issues.append(Issue("consumer", "ctfd", "type", "consumer_independence",
                            "CTFd cannot be the only consumer"))
    return ids


def _validate_evidence(issues: list[Issue], raw: Any, owner: str,
                       evidence_ids: set[str]) -> str | None:
    """Validate evidence."""
    obj = _as_mapping(issues, raw, "evidence", owner)
    eid = str(obj.get("id", owner))
    _unknown(issues, obj, EVIDENCE_KEYS, "evidence", eid)
    _require(issues, obj, ["id", "kind", "predicate", "source", "proof_fields",
                           "reset_owner", "mutates_scenario_state"], "evidence", eid)
    _validate_ident(issues, obj.get("id"), "evidence", eid, "id")
    if isinstance(obj.get("id"), str):
        _record_unique(issues, evidence_ids, obj["id"], "evidence", "id")
    if obj.get("kind") not in EVIDENCE_KINDS:
        issues.append(Issue("evidence", eid, "kind", "enum",
                            "unsupported evidence kind"))
    _require_text(issues, obj, "evidence", eid, "predicate", PREDICATE_REQUIRED)
    _require_text(issues, obj, "evidence", eid, "source", "source is required")
    fields = _as_str_list(issues, obj.get("proof_fields"), "evidence", eid,
                          "proof_fields")
    for field in fields:
        if field not in SAFE_PROOF_FIELDS:
            issues.append(Issue("evidence", eid, "proof_fields",
                                "unsafe_proof_field",
                                "proof field is not digest-safe"))
    if obj.get("mutates_scenario_state") is not False:
        issues.append(Issue("evidence", eid, "mutates_scenario_state",
                            "idempotent_validator",
                            "validator evidence must be read-only"))
    return obj.get("id") if isinstance(obj.get("id"), str) else None


def _validate_failure(issues: list[Issue], raw: Any, owner: str,
                      failure_ids: set[str]) -> str | None:
    """Validate failure."""
    obj = _as_mapping(issues, raw, "failure_state", owner)
    fid = str(obj.get("id", owner))
    _unknown(issues, obj, FAILURE_KEYS, "failure_state", fid)
    _require(issues, obj, ["id", "predicate", "severity"], "failure_state", fid)
    _validate_ident(issues, obj.get("id"), "failure_state", fid, "id")
    if isinstance(obj.get("id"), str):
        _record_unique(issues, failure_ids, obj["id"], "failure_state", "id")
    _require_text(issues, obj, "failure_state", fid, "predicate",
                  PREDICATE_REQUIRED)
    if obj.get("severity") not in FAILURE_SEVERITIES:
        issues.append(Issue("failure_state", fid, "severity", "enum",
                            "severity must be blocking or warning"))
    return obj.get("id") if isinstance(obj.get("id"), str) else None


def _validate_state_field(issues: list[Issue], obj: dict[str, Any],
                          object_type: str, object_id: str, field: str) -> None:
    """Validate state field."""
    value = obj.get(field)
    if value and not (isinstance(value, str) and _STATE_RE.match(value)):
        issues.append(Issue(object_type, object_id, field, "state_format",
                            "must look like S-STATE"))


def _validate_step_id(issues: list[Issue], obj: dict[str, Any], sid: str,
                      step_ids: set[str]) -> None:
    """Validate step id."""
    value = obj.get("id")
    if not isinstance(value, str):
        return
    if not _STEP_ID_RE.match(value):
        issues.append(Issue("path_step", sid, "id", "step_format",
                            "step id must look like 1.A or 18"))
    _record_unique(issues, step_ids, value, "path_step", "id")


def _validate_step_evidence(issues: list[Issue], obj: dict[str, Any],
                            sid: str, evidence_ids: set[str]) -> None:
    """Validate step evidence."""
    required = _as_list(issues, obj.get("required_evidence", []),
                        "path_step", sid, "required_evidence")
    optional = _as_list(issues, obj.get("optional_evidence", []),
                        "path_step", sid, "optional_evidence")
    if obj.get("classification") == "canonical" and not required:
        issues.append(Issue("path_step", sid, "required_evidence",
                            "required_evidence",
                            "canonical steps need required evidence"))
    for evidence in required:
        _validate_evidence(issues, evidence, sid, evidence_ids)
    for evidence in optional:
        _validate_evidence(issues, evidence, sid, evidence_ids)


def _validate_step_failures(issues: list[Issue], obj: dict[str, Any],
                            sid: str, failure_ids: set[str]) -> None:
    """Validate step failures."""
    failures = _as_list(issues, obj.get("failure_states", []),
                        "path_step", sid, "failure_states")
    for failure in failures:
        _validate_failure(issues, failure, sid, failure_ids)


def _validate_step_row(issues: list[Issue], raw: Any, idx: int,
                       step_ids: set[str], evidence_ids: set[str],
                       failure_ids: set[str]) -> tuple[str, list[str]]:
    """Validate step row."""
    obj = _as_mapping(issues, raw, "path_step", str(idx))
    sid = str(obj.get("id", idx))
    _unknown(issues, obj, STEP_KEYS, "path_step", sid)
    _require(issues, obj, ["id", "title", "classification"], "path_step", sid)
    _validate_step_id(issues, obj, sid, step_ids)
    if obj.get("classification") not in STEP_CLASSES:
        issues.append(Issue("path_step", sid, "classification", "enum",
                            "unsupported step classification"))
    _validate_state_field(issues, obj, "path_step", sid, "success_state")
    prereqs = _as_str_list(issues, obj.get("prerequisites", []),
                           "path_step", sid, "prerequisites")
    _validate_step_evidence(issues, obj, sid, evidence_ids)
    _validate_step_failures(issues, obj, sid, failure_ids)
    return sid, prereqs


def _validate_prereq_refs(issues: list[Issue], refs: list[tuple[str, str]],
                          step_ids: set[str]) -> None:
    """Validate prereq refs."""
    for sid, ref in refs:
        if ref not in step_ids:
            issues.append(Issue("path_step", sid, "prerequisites",
                                "unresolved_ref",
                                "prerequisite does not reference a path step"))


def _validate_steps(data: dict[str, Any], issues: list[Issue]) -> tuple[set[str], set[str], set[str]]:
    """Validate steps."""
    step_ids: set[str] = set()
    evidence_ids: set[str] = set()
    failure_ids: set[str] = set()
    prereq_refs: list[tuple[str, str]] = []

    for idx, raw in enumerate(_as_list(issues, data.get("path_steps"),
                                      "oracle", "root", "path_steps")):
        sid, prereqs = _validate_step_row(
            issues, raw, idx, step_ids, evidence_ids, failure_ids)
        prereq_refs.extend((sid, ref) for ref in prereqs)

    _validate_prereq_refs(issues, prereq_refs, step_ids)
    return step_ids, evidence_ids, failure_ids


def _validate_awards(issues: list[Issue], raw_awards: Any, object_type: str,
                     object_id: str, consumer_ids: set[str]) -> None:
    """Validate awards."""
    awards = _as_list(issues, raw_awards, object_type, object_id, "awards")
    if not awards:
        issues.append(Issue(object_type, object_id, "awards", "required",
                            "at least one award is required"))
    for idx, raw in enumerate(awards):
        obj = _as_mapping(issues, raw, "award", f"{object_id}:{idx}")
        _unknown(issues, obj, AWARD_KEYS, "award", f"{object_id}:{idx}")
        _require(issues, obj, ["consumer", "adapter", "points"],
                 "award", f"{object_id}:{idx}")
        consumer = obj.get("consumer")
        if consumer not in consumer_ids:
            issues.append(Issue("award", f"{object_id}:{idx}", "consumer",
                                "unresolved_ref",
                                "award references an unknown consumer"))
        if not isinstance(obj.get("points"), int) or obj.get("points") < 0:
            issues.append(Issue("award", f"{object_id}:{idx}", "points",
                                "points", "points must be a non-negative integer"))


def _validate_outcome_identity(issues: list[Issue], obj: dict[str, Any],
                               oid: str, outcome_ids: set[str]) -> None:
    """Validate outcome identity."""
    _validate_ident(issues, obj.get("id"), "outcome", oid, "id")
    if isinstance(obj.get("id"), str):
        _record_unique(issues, outcome_ids, obj["id"], "outcome", "id")
    if not isinstance(obj.get("required"), bool):
        issues.append(Issue("outcome", oid, "required", "type_error",
                            "required must be boolean"))
    if obj.get("required") is True and not obj.get("required_evidence"):
        issues.append(Issue("outcome", oid, "required_evidence",
                            "required_evidence",
                            "required outcomes need required evidence"))
    _validate_state_field(issues, obj, "outcome", oid, "success_state")


def _validate_known_refs(issues: list[Issue], obj: dict[str, Any],
                         object_type: str, object_id: str, field: str,
                         known: set[str], detail: str) -> None:
    """Validate known refs."""
    refs = _as_str_list(issues, obj.get(field, []), object_type, object_id, field)
    for ref in refs:
        if ref not in known:
            issues.append(Issue(object_type, object_id, field, "unresolved_ref",
                                detail))


def _validate_outcome_refs(issues: list[Issue], obj: dict[str, Any], oid: str,
                           step_ids: set[str], evidence_ids: set[str],
                           failure_ids: set[str]) -> None:
    """Validate outcome refs."""
    _validate_known_refs(issues, obj, "outcome", oid, "canonical_steps",
                         step_ids, "canonical step reference is unknown")
    _validate_known_refs(issues, obj, "outcome", oid, "required_evidence",
                         evidence_ids, REFERENCE_UNKNOWN)
    _validate_known_refs(issues, obj, "outcome", oid, "optional_evidence",
                         evidence_ids, REFERENCE_UNKNOWN)
    _validate_known_refs(issues, obj, "outcome", oid, "failure_states",
                         failure_ids, REFERENCE_UNKNOWN)


def _validate_outcome_row(issues: list[Issue], raw: Any, idx: int,
                          outcome_ids: set[str], step_ids: set[str],
                          evidence_ids: set[str], failure_ids: set[str],
                          consumer_ids: set[str]) -> None:
    """Validate outcome row."""
    obj = _as_mapping(issues, raw, "outcome", str(idx))
    oid = str(obj.get("id", idx))
    _unknown(issues, obj, OUTCOME_KEYS, "outcome", oid)
    _require(issues, obj, ["id", "title", "required", "canonical_steps",
                           "awards"], "outcome", oid)
    if "required_evidence" not in obj:
        issues.append(Issue("outcome", oid, "required_evidence",
                            "required", "missing"))
    _validate_outcome_identity(issues, obj, oid, outcome_ids)
    _validate_outcome_refs(issues, obj, oid, step_ids, evidence_ids, failure_ids)
    _validate_awards(issues, obj.get("awards"), "outcome", oid, consumer_ids)


def _validate_outcomes(data: dict[str, Any], issues: list[Issue],
                       step_ids: set[str], evidence_ids: set[str],
                       failure_ids: set[str],
                       consumer_ids: set[str]) -> set[str]:
    """Validate outcomes."""
    outcome_ids: set[str] = set()
    for idx, raw in enumerate(_as_list(issues, data.get("outcomes"),
                                      "oracle", "root", "outcomes")):
        _validate_outcome_row(
            issues, raw, idx, outcome_ids, step_ids, evidence_ids, failure_ids,
            consumer_ids)
    return outcome_ids


def _validate_alternate_identity(issues: list[Issue], obj: dict[str, Any],
                                 aid: str, alternate_ids: set[str]) -> None:
    """Validate alternate identity."""
    _validate_ident(issues, obj.get("id"), "alternate", aid, "id")
    if isinstance(obj.get("id"), str):
        _record_unique(issues, alternate_ids, obj["id"], "alternate", "id")
    _require_text(issues, obj, "alternate", aid, "predicate",
                  PREDICATE_REQUIRED)


def _validate_alternate_award(issues: list[Issue], raw_award: Any, aid: str,
                              outcome_ids: set[str]) -> None:
    """Validate alternate award."""
    award = _as_mapping(issues, raw_award, "alternate_award", aid)
    _unknown(issues, award, ALTERNATE_AWARD_KEYS, "alternate_award", aid)
    _require(issues, award, ["outcome", "points"], "alternate_award", aid)
    if award.get("outcome") not in outcome_ids:
        issues.append(Issue("alternate_award", aid, "outcome",
                            "unresolved_ref",
                            "alternate award references an unknown outcome"))
    if not isinstance(award.get("points"), int) or award.get("points") < 0:
        issues.append(Issue("alternate_award", aid, "points", "points",
                            "points must be a non-negative integer"))


def _validate_alternate_evidence(issues: list[Issue], raw_evidence: Any,
                                 aid: str) -> None:
    """Validate alternate evidence."""
    local_evidence_ids: set[str] = set()
    evidence = _as_list(issues, raw_evidence, "alternate", aid, "evidence")
    if not evidence:
        issues.append(Issue("alternate", aid, "evidence", "required",
                            "alternate needs evidence"))
    for row in evidence:
        _validate_evidence(issues, row, aid, local_evidence_ids)


def _validate_alternate_review(issues: list[Issue], raw_review: Any,
                               aid: str) -> None:
    """Validate alternate review."""
    review = _as_mapping(issues, raw_review, "alternate_review", aid)
    _unknown(issues, review, REVIEW_KEYS, "alternate_review", aid)
    _require(issues, review, ["status", "rationale"], "alternate_review", aid)
    if review.get("status") != "explicit":
        issues.append(Issue("alternate_review", aid, "status",
                            "alternate_review",
                            "alternate awards must be explicit and reviewable"))
    _require_text(issues, review, "alternate_review", aid, "rationale",
                  "review rationale is required")


def _validate_alternate_row(issues: list[Issue], raw: Any, idx: int,
                            alternate_ids: set[str],
                            outcome_ids: set[str]) -> None:
    """Validate alternate row."""
    obj = _as_mapping(issues, raw, "alternate", str(idx))
    aid = str(obj.get("id", idx))
    _unknown(issues, obj, ALTERNATE_KEYS, "alternate", aid)
    _require(issues, obj, ["id", "title", "award", "predicate", "evidence",
                           "review"], "alternate", aid)
    _validate_alternate_identity(issues, obj, aid, alternate_ids)
    _validate_alternate_award(issues, obj.get("award"), aid, outcome_ids)
    _validate_alternate_evidence(issues, obj.get("evidence"), aid)
    _validate_alternate_review(issues, obj.get("review"), aid)


def _validate_alternates(data: dict[str, Any], issues: list[Issue],
                         outcome_ids: set[str]) -> None:
    """Validate alternates."""
    alternate_ids: set[str] = set()
    for idx, raw in enumerate(_as_list(issues, data.get("accepted_alternates", []),
                                      "oracle", "root", "accepted_alternates")):
        _validate_alternate_row(issues, raw, idx, alternate_ids, outcome_ids)


def _validate_exports(data: dict[str, Any], issues: list[Issue]) -> None:
    """Validate exports."""
    audiences: set[str] = set()
    export_ids: set[str] = set()
    for idx, raw in enumerate(_as_list(issues, data.get("exports"),
                                      "oracle", "root", "exports")):
        obj = _as_mapping(issues, raw, "export", str(idx))
        eid = str(obj.get("id", idx))
        _unknown(issues, obj, EXPORT_KEYS, "export", eid)
        _require(issues, obj, ["id", "audience", "visibility", "includes"],
                 "export", eid)
        _validate_ident(issues, obj.get("id"), "export", eid, "id")
        if isinstance(obj.get("id"), str):
            _record_unique(issues, export_ids, obj["id"], "export", "id")
        audience = obj.get("audience")
        if audience not in EXPORT_AUDIENCES:
            issues.append(Issue("export", eid, "audience", "enum",
                                "unsupported export audience"))
        elif isinstance(audience, str):
            audiences.add(audience)
            expected_visibility = EXPORT_VISIBILITIES[audience]
            if obj.get("visibility") != expected_visibility:
                issues.append(Issue("export", eid, "visibility",
                                    "visibility",
                                    f"{audience} exports must be {expected_visibility}"))
        _as_str_list(issues, obj.get("includes"), "export", eid, "includes")
    for required in EXPORT_AUDIENCES:
        if required not in audiences:
            issues.append(Issue("export", required, "audience", "required",
                                "operator_debrief and agent_benchmark exports are required"))


def validate(data: dict[str, Any], source: str = "<memory>") -> list[Issue]:
    """Validate an oracle artifact and return all issues found."""
    issues: list[Issue] = []
    if not isinstance(data, dict):
        return [Issue("oracle", source, "", "type_error", "root must be a mapping")]

    _validate_top(data, issues)
    _validate_scenario(data, issues)
    _validate_visibility(data, issues)
    _validate_validator(data, issues)
    consumer_ids = _validate_consumers(data, issues)
    step_ids, evidence_ids, failure_ids = _validate_steps(data, issues)
    outcome_ids = _validate_outcomes(
        data, issues, step_ids, evidence_ids, failure_ids, consumer_ids)
    _validate_alternates(data, issues, outcome_ids)
    _validate_exports(data, issues)
    return issues


def _failure_states(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Failure states."""
    rows: list[dict[str, Any]] = []
    for step in data.get("path_steps", []):
        if isinstance(step, dict):
            rows.extend(step.get("failure_states", []) or [])
    return rows


def render_export(data: dict[str, Any], audience: str) -> dict[str, Any]:
    """Render a bounded export for an approved audience."""
    issues = validate(data)
    if issues:
        raise OracleValidationError(issues)
    if audience == "operator_debrief":
        return {
            "schema_version": data["schema_version"],
            "oracle_id": data["oracle_id"],
            "scenario": data["scenario"],
            "outcomes": data.get("outcomes", []),
            "accepted_alternates": data.get("accepted_alternates", []),
            "failure_states": _failure_states(data),
        }
    if audience == "agent_benchmark":
        return {
            "schema_version": data["schema_version"],
            "oracle_id": data["oracle_id"],
            "scenario": dict(data["scenario"]),
            "outcomes": [
                {
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "required": row.get("required"),
                    "awards": [
                        {"consumer": award.get("consumer"),
                         "points": award.get("points")}
                        for award in row.get("awards", [])
                    ],
                }
                for row in data.get("outcomes", [])
            ],
        }
    raise ValueError(f"unsupported export audience: {audience}")
