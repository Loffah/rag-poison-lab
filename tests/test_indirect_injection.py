"""Deterministic tests for the indirect_injection family. No LLM calls."""

from __future__ import annotations

from rag_poison_lab.attacks.indirect_injection import all_attacks


def test_every_payload_renders_a_document_containing_its_canary():
    for attack in all_attacks():
        assert attack.canary in attack.build_document(), (
            f"{attack.payload_id} document is missing its own canary"
        )


def test_unique_canaries_across_family():
    canaries = [a.canary for a in all_attacks()]
    assert len(set(canaries)) == len(canaries)


def test_no_payload_uses_naked_override_phrasing():
    """Indirect injection's whole point is that it doesn't say 'IGNORE
    PREVIOUS INSTRUCTIONS'. If a payload contains that phrasing it belongs
    in the direct_override family, not here."""
    for attack in all_attacks():
        doc_upper = attack.build_document().upper()
        assert "IGNORE" not in doc_upper or "IGNORE ALL PREVIOUS" not in doc_upper, (
            f"{attack.payload_id} contains naked override phrasing"
        )


def test_canary_substring_match_is_sufficient_to_land():
    """These attacks succeed if the model emits the canary anywhere in its
    response. Default Attack.landed() does substring matching, so a model
    that follows the embedded directive will land the attack."""
    attack = all_attacks()[0]
    response = f"Per the policy: {attack.canary} Refunds are processed within 30 days."
    assert attack.landed(response)


def test_attacks_span_multiple_severity_tiers():
    """The family should mix severity ratings so the report has texture."""
    severities = {a.severity for a in all_attacks()}
    assert len(severities) >= 2
