"""Attack-run loop. Each attack gets a fresh corpus state so payloads don't
contaminate each other across runs."""

from __future__ import annotations

from typing import Callable, Iterable

from .attacks.base import Attack
from .lab import VulnerableRAG
from .scoring import AttackResult, score


def run_attacks(
    rag: VulnerableRAG,
    attacks: Iterable[Attack],
    benign_corpus: list[tuple[str, str]] | None = None,
    on_attack_start: Callable[[Attack], None] | None = None,
    on_attack_done: Callable[[AttackResult], None] | None = None,
) -> list[AttackResult]:
    """Run each attack against a freshly-seeded corpus.

    For each attack:
      1. Clear the lab's document store.
      2. Ingest the benign cover corpus (so retrieval has plausible alternatives).
      3. Ingest the poisoned document.
      4. Send the probe question.
      5. Score the response.

    Optional callbacks fire before and after each attack so callers can drive
    progress UIs.
    """
    results: list[AttackResult] = []
    for attack in attacks:
        if on_attack_start:
            on_attack_start(attack)
        rag.docs = []
        if benign_corpus:
            for doc_id, content in benign_corpus:
                rag.ingest(content, doc_id=doc_id, source="corpus")
        rag.ingest(
            attack.build_document(),
            doc_id=f"poisoned-{attack.payload_id}",
            source="attacker",
        )
        response, retrieved = rag.ask(attack.probe_question())
        result = score(attack, response, [d.doc_id for d in retrieved])
        results.append(result)
        if on_attack_done:
            on_attack_done(result)
    return results
