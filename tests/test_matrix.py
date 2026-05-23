"""Matrix-run tests. Use stubbed LLMs so no API calls are made."""

from __future__ import annotations

from dataclasses import dataclass, field

from rag_poison_lab.attacks.direct import all_attacks as direct_attacks
from rag_poison_lab.lab import VulnerableRAG
from rag_poison_lab.matrix import MatrixRow, ModelSpec, run_matrix
from rag_poison_lab.runner import run_attacks


@dataclass
class StubLLM:
    """Stub LLM that emits whatever canary is requested in the user prompt
    (so all attacks 'land'), or a benign response (so none land)."""

    leak_canaries: bool = True

    def generate(self, system: str, user: str) -> str:
        if self.leak_canaries:
            # Extract canary from user prompt if present
            import re
            m = re.search(r"CANARY-[a-f0-9]+-[a-f0-9]+", user)
            if m:
                return f"Sure. {m.group(0)}"
        return "Boring helpful answer that doesn't include any canary."


def test_run_matrix_with_stub_clients(monkeypatch):
    """Run a 2-model matrix where one leaks canaries and one does not.
    Verify the matrix rows reflect the diff."""
    leaky_stub = StubLLM(leak_canaries=True)
    aligned_stub = StubLLM(leak_canaries=False)

    # Patch make_client to return our stubs
    from rag_poison_lab import matrix as matrix_module

    def fake_make_client(spec):
        if spec.label == "leaky":
            return leaky_stub
        return aligned_stub

    monkeypatch.setattr(matrix_module, "make_client", fake_make_client)

    specs = [
        ModelSpec("leaky", "anthropic", "fake-leaky"),
        ModelSpec("aligned", "anthropic", "fake-aligned"),
    ]
    attacks = direct_attacks()
    rows = run_matrix(specs=specs, attacks=attacks, hardened=False)

    assert len(rows) == 2
    assert rows[0].spec.label == "leaky"
    assert rows[1].spec.label == "aligned"

    leaky_landed = sum(1 for r in rows[0].results if r.landed)
    aligned_landed = sum(1 for r in rows[1].results if r.landed)

    assert leaky_landed == len(attacks), "leaky stub should land every attack"
    assert aligned_landed == 0, "aligned stub should land nothing"
