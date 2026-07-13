"""ACES scenario-pack definition and authoring/validation tooling.

This package bundles the canonical scenario-pack schemas, template, shared oracle
model, and contract source (under ``resources/``) together with the tools that
enforce them, so consumers install one version-matched artifact instead of
vendoring the contract.
"""

from importlib.metadata import version

from .digest import (
    PackDigestError,
    derive_pack_content_manifest,
    pack_content_digest,
    validate_pack_content_manifest,
    verify_pack_content_digest,
)

# The version lives in pyproject.toml ([project].version), bumped by release-please
# (ADR 0008); __version__ derives from the installed package metadata.
__version__ = version("aces-scenario-packs")

__all__ = [
    "__version__",
    "PackDigestError",
    "derive_pack_content_manifest",
    "pack_content_digest",
    "validate_pack_content_manifest",
    "verify_pack_content_digest",
]
