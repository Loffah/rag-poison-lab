"""Deterministic tests for the multilingual_bypass family. No LLM calls."""

from __future__ import annotations

from rag_poison_lab.attacks.multilingual_bypass import all_attacks


def test_every_payload_renders_a_document_containing_its_canary():
    for attack in all_attacks():
        assert attack.canary in attack.build_document(), (
            f"{attack.payload_id} document is missing its own canary"
        )


def test_unique_canaries_across_family():
    canaries = [a.canary for a in all_attacks()]
    assert len(set(canaries)) == len(canaries)


def test_norwegian_full_uses_norwegian_text():
    """Sanity check: norwegian_full should contain Norwegian-only override
    phrasing. If someone accidentally swaps in English the test fires."""
    attack = next(a for a in all_attacks() if a.payload_id == "norwegian_full")
    document = attack.build_document()
    assert "IGNORER" in document.upper()
    assert "IGNORE ALL PREVIOUS" not in document.upper()


def test_norwegian_embedded_keeps_english_body():
    """The embedded variant smuggles the foreign-language injection into an
    otherwise-English document. The English business content must survive."""
    attack = next(a for a in all_attacks() if a.payload_id == "norwegian_embedded")
    document = attack.build_document()
    assert "refund" in document.lower()
    assert "VIKTIG" in document


def test_probe_question_is_english_across_all_variants():
    """The probe question stays in English so the language of the question
    doesn't itself signal the language of the attack."""
    for attack in all_attacks():
        question_lower = attack.probe_question().lower()
        assert "what is our refund policy" in question_lower
