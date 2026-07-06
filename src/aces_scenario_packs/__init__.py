"""ACES scenario-pack definition and authoring/validation tooling.

This package bundles the canonical scenario-pack schemas, template, shared oracle
model, and contract source (under ``resources/``) together with the tools that
enforce them, so consumers install one version-matched artifact instead of
vendoring the contract.
"""

# Single committed source of truth for the version (ADR 0007). tools/release.py
# bumps this from the towncrier fragments; hatchling reads it via
# [tool.hatch.version] path. Do not edit by hand.
__version__ = "0.1.0"
