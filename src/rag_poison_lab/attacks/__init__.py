"""Attack family registry. Aggregates every family into a single list."""

from __future__ import annotations

from .base import Attack
from .direct import all_attacks as _direct_attacks
from .format_spoofing import all_attacks as _format_spoofing_attacks
from .hidden_text import all_attacks as _hidden_text_attacks
from .indirect_injection import all_attacks as _indirect_injection_attacks
from .markdown_exfil import all_attacks as _markdown_exfil_attacks
from .multi_hop import all_attacks as _multi_hop_attacks
from .multilingual_bypass import all_attacks as _multilingual_bypass_attacks
from .tool_call_hijack import all_attacks as _tool_call_hijack_attacks


def all_attacks() -> list[Attack]:
    """All attack-family payloads, in deterministic ordering."""
    return [
        *_direct_attacks(),
        *_indirect_injection_attacks(),
        *_markdown_exfil_attacks(),
        *_multilingual_bypass_attacks(),
        *_hidden_text_attacks(),
        *_format_spoofing_attacks(),
        *_multi_hop_attacks(),
        *_tool_call_hijack_attacks(),
    ]
