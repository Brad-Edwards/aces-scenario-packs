#!/usr/bin/env python3
"""Scenario-pack identity through ACES associated-artifact manifests.

The portable parent/reference/checksum/set model and canonicalization belong to
ACES (ADR-077).  This module supplies only the scenario-pack side of that
boundary: pack-local locator resolution, descriptor-anchored materialization,
exact inventory coverage, SDL-parent selection, and small compute/verify
conveniences for consumers.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import stat
import unicodedata
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, cast
from urllib.parse import quote, unquote_to_bytes, urlsplit

import yaml
from aces_contracts.associated_artifacts import (
    AssociatedArtifactValidationLimits,
    associated_artifact_set_digest,
    load_associated_artifact_manifest_json,
    validate_associated_artifact_manifest,
)
from aces_contracts.contracts import AssociatedArtifactManifestModel
from aces_contracts.diagnostics import Diagnostic
from aces_sdl import SDLError, parse_sdl_file

_MANIFEST_POINTER = "associated_artifact_manifest"
_PACK_MANIFEST = "pack.yaml"
_PACK_URI_SCHEME = "aces-scenario-pack"
_CANONICAL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CACHE_PREFIX = ("sdl", ".aces", "module-cache")
_READ_CHUNK = 64 * 1024
_MAX_PACK_YAML_BYTES = 1024 * 1024
_MAX_MANIFEST_BYTES = 8 * 1024 * 1024
_MAX_PACK_MEMBERS = 1024

_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
_BINARY = getattr(os, "O_BINARY", 0)


class PackDigestError(ValueError):
    """The pack cannot produce or verify one conforming ACES set identity.

    Messages are deliberately bounded and payload-free.  When ACES semantic
    validation ran, its structured diagnostics remain available to callers via
    :attr:`diagnostics` without being flattened into an unbounded exception.
    """

    def __init__(self, message: str, diagnostics: tuple[Diagnostic, ...] = ()) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


def _require_descriptor_platform() -> None:
    if not _NOFOLLOW or not _DIRECTORY or os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd:
        raise PackDigestError("descriptor-anchored pack reads are unsupported on this platform")


def _open_root(pack_root: str | os.PathLike[str]) -> tuple[str, int]:
    _require_descriptor_platform()
    root = os.fspath(pack_root)
    if not root:
        raise PackDigestError("pack root is empty")
    try:
        if os.path.islink(root):
            raise PackDigestError("pack root is a symlink")
        fd = os.open(root, os.O_RDONLY | _DIRECTORY | _NOFOLLOW)
        root_stat = os.fstat(fd)
    except PackDigestError:
        raise
    except OSError as exc:
        raise PackDigestError("pack root is not an accessible directory") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        os.close(fd)
        raise PackDigestError("pack root is not a directory")
    return os.path.realpath(root), fd


def _normalize_component(name: str) -> str:
    normalized = unicodedata.normalize("NFC", name)
    if name != normalized or not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise PackDigestError("pack member name is not canonical")
    try:
        name.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise PackDigestError("pack member name is not valid UTF-8") from exc
    return name


def _normalize_relpath(value: str) -> str:
    if not isinstance(value, str) or not value or os.path.isabs(value) or "\\" in value:
        raise PackDigestError("pack-relative path is not canonical")
    parts = value.split("/")
    normalized = "/".join(_normalize_component(part) for part in parts)
    if normalized != value:
        raise PackDigestError("pack-relative path is not canonical")
    return normalized


def _is_cache_path(parts: tuple[str, ...]) -> bool:
    return parts[: len(_CACHE_PREFIX)] == _CACHE_PREFIX


def _walk_directory(
    directory_fd: int,
    prefix: tuple[str, ...],
    excluded: str,
    seen_casefold: dict[str, str],
) -> Iterator[str]:
    try:
        names = sorted(os.listdir(directory_fd))
    except OSError as exc:
        raise PackDigestError("pack directory could not be traversed") from exc
    for raw_name in names:
        name = _normalize_component(raw_name)
        parts = (*prefix, name)
        rel = "/".join(parts)
        folded = rel.casefold()
        prior = seen_casefold.get(folded)
        if prior is not None and prior != rel:
            raise PackDigestError("pack contains a case-insensitive path collision")
        seen_casefold[folded] = rel
        try:
            member_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as exc:
            raise PackDigestError("pack member could not be inspected") from exc
        if stat.S_ISLNK(member_stat.st_mode):
            raise PackDigestError("pack contains a symlink")
        if stat.S_ISDIR(member_stat.st_mode):
            if _is_cache_path(parts):
                continue
            try:
                child_fd = os.open(name, os.O_RDONLY | _DIRECTORY | _NOFOLLOW, dir_fd=directory_fd)
            except OSError as exc:
                raise PackDigestError("pack directory could not be opened") from exc
            try:
                yield from _walk_directory(child_fd, parts, excluded, seen_casefold)
            finally:
                os.close(child_fd)
            continue
        if not stat.S_ISREG(member_stat.st_mode):
            raise PackDigestError("pack contains a non-regular file")
        if member_stat.st_nlink > 1:
            raise PackDigestError("pack contains a multiply-linked file")
        if rel != excluded:
            yield rel


def _inventory(root_fd: int, excluded: str) -> tuple[str, ...]:
    members = tuple(_walk_directory(root_fd, (), excluded, {}))
    if len(members) > _MAX_PACK_MEMBERS:
        raise PackDigestError("pack member count exceeds the validation limit")
    return members


def _open_member(root_fd: int, rel: str) -> int:
    parts = _normalize_relpath(rel).split("/")
    current_fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | _DIRECTORY | _NOFOLLOW, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(
            parts[-1], os.O_RDONLY | _NOFOLLOW | _NONBLOCK | _BINARY, dir_fd=current_fd
        )
    except OSError as exc:
        raise PackDigestError("pack member could not be opened") from exc
    finally:
        os.close(current_fd)
    member_stat = os.fstat(file_fd)
    if not stat.S_ISREG(member_stat.st_mode) or member_stat.st_nlink > 1:
        os.close(file_fd)
        raise PackDigestError("pack member is not a singly-linked regular file")
    return file_fd


def _read_member_bytes(root_fd: int, rel: str, *, max_bytes: int) -> bytes:
    fd = _open_member(root_fd, rel)
    chunks: list[bytes] = []
    try:
        total = 0
        while chunk := os.read(fd, min(_READ_CHUNK, max_bytes + 1 - total)):
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise PackDigestError("pack metadata exceeds the validation limit")
    except OSError as exc:
        raise PackDigestError("pack member could not be read") from exc
    finally:
        os.close(fd)
    return b"".join(chunks)


class _DescriptorReader:
    """Lazy, no-follow reader so ACES opens only the payload being validated."""

    def __init__(self, root_fd: int, rel: str) -> None:
        self._root_fd = root_fd
        self._rel = rel
        self._fd: int | None = None
        self._done = False

    def read(self, size: int = -1) -> bytes:
        if self._done:
            return b""
        if self._fd is None:
            self._fd = _open_member(self._root_fd, self._rel)
        read_size = _READ_CHUNK if size is None or size < 0 else size
        try:
            chunk = os.read(self._fd, read_size)
        except OSError as exc:
            self.close()
            raise OSError("pack payload read failed") from exc
        if not chunk:
            self.close()
            self._done = True
        return chunk

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


def _pack_uri_to_rel(uri: str, excluded: str) -> str:
    parsed = urlsplit(uri)
    if (
        parsed.scheme != _PACK_URI_SCHEME
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
    ):
        raise PackDigestError("associated artifact URI is not a canonical pack locator")
    try:
        rel = unquote_to_bytes(parsed.path[1:]).decode("utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise PackDigestError("associated artifact URI is not valid UTF-8") from exc
    rel = _normalize_relpath(rel)
    canonical = f"{_PACK_URI_SCHEME}:/{quote(rel, safe='/-._~')}"
    if uri != canonical or rel == excluded or _is_cache_path(tuple(rel.split("/"))):
        raise PackDigestError("associated artifact URI is not a canonical pack locator")
    return rel


def _load_pack_metadata(root_fd: int) -> tuple[str, str, str]:
    try:
        payload = yaml.safe_load(
            _read_member_bytes(root_fd, _PACK_MANIFEST, max_bytes=_MAX_PACK_YAML_BYTES).decode("utf-8")
        )
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PackDigestError("pack.yaml is not valid UTF-8 YAML") from exc
    if not isinstance(payload, dict):
        raise PackDigestError("pack.yaml is not a mapping")
    name = payload.get("name")
    version = payload.get("version")
    pointer = payload.get(_MANIFEST_POINTER)
    if not isinstance(name, str) or not name or not isinstance(pointer, str):
        raise PackDigestError("pack identity or associated-artifact manifest pointer is missing")
    if not isinstance(version, (str, int, float)):
        raise PackDigestError("pack version is missing")
    return name, str(version), _normalize_relpath(pointer)


def _load_manifest(root_fd: int, manifest_rel: str) -> AssociatedArtifactManifestModel:
    try:
        return load_associated_artifact_manifest_json(
            _read_member_bytes(root_fd, manifest_rel, max_bytes=_MAX_MANIFEST_BYTES)
        )
    except PackDigestError:
        raise
    except (ValueError, TypeError) as exc:
        raise PackDigestError("associated artifact manifest is structurally invalid") from exc


def _validate_pack_manifest_identity(
    manifest: AssociatedArtifactManifestModel, name: str, version: str
) -> None:
    if (
        manifest.scope != "scenario"
        or manifest.parent_ref.ref_id != name
        or manifest.manifest_id != f"{name}-associated-artifacts"
        or manifest.manifest_version != version
    ):
        raise PackDigestError("associated artifact manifest does not match pack identity")


def _artifact_paths(manifest: AssociatedArtifactManifestModel, excluded: str) -> dict[str, str]:
    paths: dict[str, str] = {}
    for artifact_id, artifact in manifest.artifacts.items():
        if artifact.checksum.algorithm != "sha256":
            raise PackDigestError("scenario-pack artifacts must use sha256 checksums")
        paths[artifact_id] = _pack_uri_to_rel(artifact.uri, excluded)
    return paths


def _parse_parent_candidates(root: str, inventory: tuple[str, ...]) -> tuple[object, ...]:
    sdl_docs = [rel for rel in inventory if rel.startswith("sdl/") and rel.count("/") == 1 and rel.endswith(".sdl.yaml")]
    if not sdl_docs:
        raise PackDigestError("pack has no direct SDL parent document")
    candidates: list[object] = []
    for rel in sdl_docs:
        try:
            candidates.append(parse_sdl_file(Path(root, *rel.split("/"))))
        except (SDLError, OSError) as exc:
            raise PackDigestError("pack SDL parent is invalid") from exc
    return tuple(candidates)


def _reader_map(root_fd: int, paths: Mapping[str, str]) -> dict[str, _DescriptorReader]:
    return {artifact_id: _DescriptorReader(root_fd, rel) for artifact_id, rel in paths.items()}


def _validate_with_parent_candidates(
    manifest: AssociatedArtifactManifestModel,
    candidates: tuple[object, ...],
    root_fd: int,
    paths: Mapping[str, str],
    limits: AssociatedArtifactValidationLimits | None,
) -> None:
    best: tuple[Diagnostic, ...] = ()
    for parent in candidates:
        readers = _reader_map(root_fd, paths)
        try:
            diagnostics = validate_associated_artifact_manifest(
                manifest,
                parent=parent,
                artifact_readers=cast(Mapping[str, BinaryIO], readers),
                limits=limits,
            )
        finally:
            for reader in readers.values():
                reader.close()
        if not diagnostics:
            return
        if not best or sum(item.code == "associated-artifact.parent-mismatch" for item in diagnostics) < sum(
            item.code == "associated-artifact.parent-mismatch" for item in best
        ):
            best = diagnostics
    raise PackDigestError("associated artifact manifest failed ACES byte binding", best)


@contextmanager
def _pack_context(pack_root: str | os.PathLike[str]):
    root, root_fd = _open_root(pack_root)
    try:
        name, version, manifest_rel = _load_pack_metadata(root_fd)
        manifest = _load_manifest(root_fd, manifest_rel)
        _validate_pack_manifest_identity(manifest, name, version)
        inventory = _inventory(root_fd, manifest_rel)
        paths = _artifact_paths(manifest, manifest_rel)
        if set(paths.values()) != set(inventory):
            raise PackDigestError("associated artifact manifest does not cover the exact pack inventory")
        candidates = _parse_parent_candidates(root, inventory)
        yield root_fd, manifest_rel, manifest, inventory, paths, candidates
    finally:
        os.close(root_fd)


def _derived_manifest(
    manifest: AssociatedArtifactManifestModel,
    root_fd: int,
    paths: Mapping[str, str],
    limits: AssociatedArtifactValidationLimits | None,
) -> AssociatedArtifactManifestModel:
    active_limits = limits or AssociatedArtifactValidationLimits()
    if len(manifest.artifacts) > active_limits.max_artifacts:
        raise PackDigestError("artifact count exceeds the derivation limit")
    artifacts = {}
    total_size = 0
    for artifact_id, artifact in manifest.artifacts.items():
        fd = _open_member(root_fd, paths[artifact_id])
        digest_value = hashlib.sha256()
        size = 0
        try:
            while chunk := os.read(fd, _READ_CHUNK):
                digest_value.update(chunk)
                size += len(chunk)
                total_size += len(chunk)
                if size > active_limits.max_artifact_bytes or total_size > active_limits.max_total_bytes:
                    raise PackDigestError("artifact bytes exceed the derivation limits")
        except OSError as exc:
            raise PackDigestError("pack member could not be read") from exc
        finally:
            os.close(fd)
        checksum = artifact.checksum.model_copy(update={"value": digest_value.hexdigest()})
        artifacts[artifact_id] = artifact.model_copy(update={"checksum": checksum, "size_bytes": size})
    derived = manifest.model_copy(update={"artifacts": artifacts, "set_digest": "sha256:" + "0" * 64})
    return derived.model_copy(update={"set_digest": associated_artifact_set_digest(derived)})


def derive_pack_content_manifest(
    pack_root: str | os.PathLike[str],
    *,
    limits: AssociatedArtifactValidationLimits | None = None,
) -> AssociatedArtifactManifestModel:
    """Derive a fully byte-bound ACES manifest from one immutably staged pack.

    Descriptor metadata and pack-local locators come from the declared manifest;
    checksum values, sizes, and the set digest are recomputed from current bytes.
    The returned model is suitable for authoring/release tooling to persist.
    """

    with _pack_context(pack_root) as (root_fd, excluded, manifest, inventory, paths, candidates):
        derived = _derived_manifest(manifest, root_fd, paths, limits)
        _validate_with_parent_candidates(derived, candidates, root_fd, paths, limits)
        if _inventory(root_fd, excluded) != inventory:
            raise PackDigestError("pack file set changed during identity derivation")
        return derived


def validate_pack_content_manifest(
    pack_root: str | os.PathLike[str],
    *,
    limits: AssociatedArtifactValidationLimits | None = None,
) -> AssociatedArtifactManifestModel:
    """Return the declared manifest after full ACES parent/set/byte validation."""

    with _pack_context(pack_root) as (root_fd, excluded, manifest, inventory, paths, candidates):
        _validate_with_parent_candidates(manifest, candidates, root_fd, paths, limits)
        if _inventory(root_fd, excluded) != inventory:
            raise PackDigestError("pack file set changed during manifest validation")
        return manifest


def pack_content_digest(pack_root: str | os.PathLike[str]) -> str:
    """Return the validated ACES associated-artifact set digest for a pack."""

    return validate_pack_content_manifest(pack_root).set_digest


def verify_pack_content_digest(pack_root: str | os.PathLike[str], expected_digest: str) -> bool:
    """Return whether current validated pack bytes have ``expected_digest``."""

    if not isinstance(expected_digest, str) or _CANONICAL_DIGEST_RE.fullmatch(expected_digest) is None:
        raise PackDigestError("expected digest is not canonical sha256")
    return hmac.compare_digest(pack_content_digest(pack_root), expected_digest)


__all__ = [
    "PackDigestError",
    "derive_pack_content_manifest",
    "pack_content_digest",
    "validate_pack_content_manifest",
    "verify_pack_content_digest",
]
