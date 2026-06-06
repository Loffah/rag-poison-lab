"""Deterministic tests for the hidden_text family. No LLM calls.

These verify two things: each payload is well-formed (carries its own canary,
in encoded form for the base64 variant), and the hardened-mode ingest
sanitizer actually neutralizes the hidden payload — which is the whole point
of this family. The parser-layer defense is what hidden_text is designed to
exercise, so if sanitize_ingest stopped removing these the family's
naive-vs-hardened delta would silently go to zero.
"""

from __future__ import annotations

import base64

from rag_poison_lab.attacks.hidden_text import all_attacks
from rag_poison_lab.lab import sanitize_ingest


def _canary_reachable(text: str, canary: str) -> bool:
    """True if the canary is recoverable from text either as a literal or by
    decoding a base64 segment. Used to confirm sanitization actually removed
    the payload rather than just re-encoding it."""
    if canary in text:
        return True
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 16:
            continue
        try:
            if canary in base64.b64decode(line, validate=True).decode("utf-8", "ignore"):
                return True
        except Exception:
            pass
    return False


def test_every_payload_carries_its_canary():
    """Every payload must encode its own canary somewhere in the document so
    the attack has a unique token to score against."""
    for attack in all_attacks():
        assert _canary_reachable(attack.build_document(), attack.canary), (
            f"{attack.payload_id} document does not carry its canary"
        )


def test_unique_canaries_across_family():
    canaries = [a.canary for a in all_attacks()]
    assert len(set(canaries)) == len(canaries)


def test_base64_variant_encodes_the_live_canary():
    """The base64 payload must encode the per-instance canary, not a static
    placeholder. Regression guard against the bug where the blob was a fixed
    string that decoded to the literal '<CANARY>' template token."""
    attack = next(a for a in all_attacks() if a.payload_id == "base64_payload")
    document = attack.build_document()
    assert "<CANARY>" not in document, "template placeholder leaked into the document"
    assert attack.canary not in document, "canary should be encoded, not left as plaintext"
    assert _canary_reachable(document, attack.canary), "canary not recoverable from the base64 blob"


def test_removal_variants_are_neutralized_by_ingest_sanitizer():
    """For the variants whose payload is hidden inside a removable structure
    (HTML comment, invisible span, base64 blob), the canary must be gone after
    hardened-mode sanitization — no exfil-able token survives ingest."""
    removed = {"html_comment", "white_on_white", "font_size_zero", "base64_payload"}
    for attack in all_attacks():
        if attack.payload_id not in removed:
            continue
        cleaned = sanitize_ingest(attack.build_document())
        assert not _canary_reachable(cleaned, attack.canary), (
            f"{attack.payload_id}: canary survived ingest sanitization"
        )


def test_zero_width_variant_is_deobfuscated_not_dropped():
    """The zero-width interleave variant is de-obfuscated rather than deleted:
    the invisible characters are stripped so the instruction becomes plainly
    visible (to a human auditor and to instruction/data separation), but the
    text itself is not removed."""
    attack = next(a for a in all_attacks() if a.payload_id == "zero_width_interleave")
    cleaned = sanitize_ingest(attack.build_document())
    assert "​" not in cleaned, "zero-width characters were not stripped"
    assert "append the trace token" in cleaned, "de-obfuscated instruction text should be readable"
