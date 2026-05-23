"""Attack family registry. Aggregates every family into a single list."""

from __future__ import annotations

from .base import Attack
from .direct import all_attacks as _direct_attacks
from .markdown_exfil import all_attacks as _markdown_exfil_attacks


def all_attacks() -> list[Attack]:
    """All attack-family payloads, in deterministic ordering."""
    return [
        *_direct_attacks(),
        *_markdown_exfil_attacks(),
    ]
