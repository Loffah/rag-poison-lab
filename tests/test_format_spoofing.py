"""Deterministic tests for the format_spoofing family. No LLM calls.

This family impersonates the structural format of a trusted message inside the
retrieved document body. The defense layer is the document trust model
(provenance), which the lab approximates only via the instruction/data
separation of hardened mode — there is no provenance system to assert against
here. So these tests verify payload well-formedness and that each variant
actually carries the spoofed structural marker it claims to.
"""

from __future__ import annotations

from rag_poison_lab.attacks.format_spoofing import all_attacks
from rag_poison_lab.lab import VulnerableRAG


class _StubLLM:
    last_user: str = ""

    def generate(self, system: str, user: str) -> str:
        self.last_user = user
        return "ok"


def test_every_payload_renders_a_document_containing_its_canary():
    for attack in all_attacks():
        assert attack.canary in attack.build_document(), (
            f"{attack.payload_id} document is missing its own canary"
        )


def test_unique_canaries_across_family():
    canaries = [a.canary for a in all_attacks()]
    assert len(set(canaries)) == len(canaries)


def test_payloads_have_at_least_two_severities():
    severities = {a.severity for a in all_attacks()}
    assert len(severities) >= 2


def test_each_variant_carries_its_spoofed_marker():
    """Each variant's distinguishing feature is the trusted-format token it
    impersonates. If a refactor dropped the marker, the variant would collapse
    into a plain indirect_injection and lose its reason to exist."""
    markers = {
        "fake_system_block": "<system",
        "fake_assistant_turn": "Assistant:",
        "fake_tool_output": "\"tool\"",
        "compliance_stamp": "SOC 2",
        "cve_advisory": "CVE-",
    }
    by_id = {a.payload_id: a for a in all_attacks()}
    for payload_id, marker in markers.items():
        assert payload_id in by_id, f"missing expected variant {payload_id}"
        assert marker in by_id[payload_id].build_document(), (
            f"{payload_id} no longer contains its spoofed marker {marker!r}"
        )


def test_hardened_render_neutralizes_tag_and_transcript_spoofs():
    """End-to-end: every variant ingested into the hardened lab should come out
    with its <system>-style tags and faked assistant turns neutralized, and
    stamped with the untrusted-trust provenance envelope. Header/JSON spoofs
    have no structural token to strip, so we only assert the envelope for those."""
    for attack in all_attacks():
        stub = _StubLLM()
        rag = VulnerableRAG(llm=stub, hardened=True)
        rag.ingest(attack.build_document(), doc_id="poisoned", source="attacker")
        rag.ask(attack.probe_question())
        rendered = stub.last_user

        assert 'trust="untrusted"' in rendered, f"{attack.payload_id}: no trust envelope"
        assert "<system" not in rendered.lower(), f"{attack.payload_id}: system tag survived"
        assert not any(
            line.strip().lower().startswith("assistant:") for line in rendered.splitlines()
        ), f"{attack.payload_id}: faked assistant turn survived"
