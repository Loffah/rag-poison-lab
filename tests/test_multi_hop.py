"""Deterministic tests for the multi_hop family. No LLM calls."""

from __future__ import annotations

from rag_poison_lab.attacks.multi_hop import all_attacks
from rag_poison_lab.lab import VulnerableRAG
from rag_poison_lab.runner import run_attacks


class _Capture:
    def __init__(self) -> None:
        self.last_user = ""

    def generate(self, system: str, user: str) -> str:
        self.last_user = user
        return "stub answer"


_BENIGN = [
    ("refunds", "Our refund policy covers orders within 30 days."),
    ("hours", "Office hours are 9 to 5, Monday to Friday."),
]


def test_every_variant_plants_multiple_documents():
    for attack in all_attacks():
        docs = attack.build_documents()
        assert len(docs) >= 2, f"{attack.payload_id} is not actually multi-document"


def test_canary_is_reachable_across_the_document_set():
    """The payload canary must live in at least one hop (it need not be in every
    hop — pointer/split variants keep one document clean)."""
    for attack in all_attacks():
        docs = attack.build_documents()
        assert any(attack.canary in d for d in docs), (
            f"{attack.payload_id}: canary missing from all hops"
        )


def test_unique_canaries_across_family():
    canaries = [a.canary for a in all_attacks()]
    assert len(set(canaries)) == len(canaries)


def test_single_blob_form_contains_the_canary():
    """build_document() (the compatibility single-blob form) should still carry
    the canary so any incidental caller sees the full payload."""
    for attack in all_attacks():
        assert attack.canary in attack.build_document()


def test_all_hops_are_retrieved_together_at_default_k():
    """The whole premise is that retrieval pulls every hop into context at once.
    Run each attack through the lab and confirm a distinctive token from each
    hop reaches the model's prompt."""
    markers = {
        "split_directive": ["RPL-AUDIT", "glossary"],
        "pointer_chain": ["Refund Response Format", "verification marker"],
        "assembled_payload": ["part 1 of 2", "part 2 of 2"],
        "cross_corroboration": ["Policy team note", "Refund policy FAQ"],
    }
    by_id = {a.payload_id: a for a in all_attacks()}
    for payload_id, hop_markers in markers.items():
        cap = _Capture()
        rag = VulnerableRAG(llm=cap)
        run_attacks(rag, [by_id[payload_id]], benign_corpus=_BENIGN)
        for marker in hop_markers:
            assert marker in cap.last_user, (
                f"{payload_id}: hop marker {marker!r} did not reach the prompt"
            )
