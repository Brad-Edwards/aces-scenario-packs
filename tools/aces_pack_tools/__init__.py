"""Static, offline validation and release-check tooling for ACES scenario packs.

Stdlib-only. Every check reuses the published schema index
(``schemas/index.json``) as the single source of truth for schema families; the
package never redefines ACES SDL semantics or the scenario-pack contract, never
requires private repository state, credentials, or network access, and treats a
pack root as untrusted input. See ``docs/tooling-design-guardrails.md`` and
``tools/README.md``.
"""

from .model import Finding
from .schema import SchemaIndex, conformance_errors, load_index

__all__ = ["Finding", "SchemaIndex", "conformance_errors", "load_index"]
__version__ = "0.1.0"
