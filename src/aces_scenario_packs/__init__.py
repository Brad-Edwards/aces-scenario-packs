"""ACES scenario-pack definition and authoring/validation tooling.

This package bundles the canonical scenario-pack schemas, template, shared oracle
model, and contract source (under ``resources/``) together with the tools that
enforce them, so consumers install one version-matched artifact instead of
vendoring the contract.
"""

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("aces-scenario-packs")
except PackageNotFoundError:
    # Running from a source tree without installed package metadata.
    __version__ = "0.0.0"
