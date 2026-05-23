"""Attack interface. Each attack family produces concrete Attack instances
that the runner ingests into the lab and probes for behavior change."""

from __future__ import annotations

from dataclasses import dataclass, field
from secrets import token_hex


def make_canary() -> str:
    """Generate a fresh canary token unique per attack instance.

    Format: CANARY-<6 hex>-<6 hex>. Random enough that false-positive matches
    in normal LLM output are effectively impossible.
    """
    return f"CANARY-{token_hex(3)}-{token_hex(3)}"


@dataclass
class Attack:
    family: str
    payload_id: str
    description: str
    severity: str
    canary: str = field(default_factory=make_canary)

    def build_document(self) -> str:
        """Return the poisoned document content to ingest into the corpus."""
        raise NotImplementedError

    def probe_question(self) -> str:
        """Return the user question to ask after ingest."""
        raise NotImplementedError
