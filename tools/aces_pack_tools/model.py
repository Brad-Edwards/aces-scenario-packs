"""Sanitized, actionable finding record shared by every check.

A ``Finding`` carries a check name, a pack-relative path, an optional schema
family or gate name, and a concise reason. It never carries file contents,
environment values, tokens, or absolute paths: the tooling guardrails forbid
dumping those into errors, logs, or evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class Finding:
    check: str
    path: str
    message: str
    family: Optional[str] = None
    severity: str = "error"

    def to_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}

    def format_text(self) -> str:
        location = self.path or "<pack>"
        family = f" [{self.family}]" if self.family else ""
        return f"{self.severity.upper()} {self.check}{family}: {location}: {self.message}"
