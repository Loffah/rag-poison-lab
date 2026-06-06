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
      3. Ingest the poisoned document(s). Most attacks plant one, multi_hop
         plants several.
      4. Expose the tool surface the attack needs, if any (tool_call_hijack).
      5. Send the probe question.
      6. Score the response.

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
        poisoned = attack.build_documents()
        for j, content in enumerate(poisoned):
            # Single-doc attacks keep their familiar `poisoned-<id>` doc id;
            # multi-doc attacks get a `-0`, `-1`, ... suffix per hop.
            suffix = "" if len(poisoned) == 1 else f"-{j}"
            rag.ingest(
                content,
                doc_id=f"poisoned-{attack.payload_id}{suffix}",
                source="attacker",
            )
        rag.tools = attack.tools()
        response, retrieved = rag.ask(attack.probe_question())
        result = score(attack, response, [d.doc_id for d in retrieved])
        results.append(result)
        if on_attack_done:
            on_attack_done(result)
    return results
