"""Scoring tests. No LLM calls — these verify the detection logic deterministically."""

from __future__ import annotations

from rag_poison_lab.attacks.base import Attack, make_canary
from rag_poison_lab.attacks.direct import all_attacks
from rag_poison_lab.scoring import detect_canary, score


def test_detect_canary_finds_literal_match():
    assert detect_canary("here is your token CANARY-abc-def in the wild", "CANARY-abc-def")


def test_detect_canary_misses_when_absent():
    assert not detect_canary("this is an ordinary helpful response", "CANARY-abc-def")


def test_make_canary_is_unique_across_calls():
    seen = {make_canary() for _ in range(100)}
    assert len(seen) == 100


def test_score_marks_landed_when_canary_emitted():
    attack = all_attacks()[0]
    result = score(attack, f"Sure, here is what you asked: {attack.canary}", ["poisoned-x"])
    assert result.landed
    assert attack.canary in result.notes


def test_score_marks_not_landed_when_canary_missing():
    attack = all_attacks()[0]
    result = score(attack, "Refunds are processed within 30 days.", ["doc-000"])
    assert not result.landed
    assert "not detected" in result.notes


def test_every_direct_attack_has_unique_canary():
    canaries = [a.canary for a in all_attacks()]
    assert len(set(canaries)) == len(canaries)


def test_every_direct_attack_renders_a_document_containing_its_canary():
    for attack in all_attacks():
        assert attack.canary in attack.build_document(), (
            f"{attack.payload_id} document is missing its own canary"
        )
