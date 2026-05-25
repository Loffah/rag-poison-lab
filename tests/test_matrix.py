"""Matrix-run tests. Use stubbed LLMs so no API calls are made."""

from __future__ import annotations

from dataclasses import dataclass

from rag_poison_lab.attacks.direct import all_attacks as direct_attacks
from rag_poison_lab.matrix import MatrixRow, ModelSpec, run_matrix


@dataclass
class StubLLM:
    """Stub LLM that emits whatever canary is requested in the user prompt
    (so all attacks 'land'), or a benign response (so none land)."""

    leak_canaries: bool = True

    def generate(self, system: str, user: str) -> str:
        if self.leak_canaries:
            import re
            m = re.search(r"CANARY-[a-f0-9]+-[a-f0-9]+", user)
            if m:
                return f"Sure. {m.group(0)}"
        return "Boring helpful answer that doesn't include any canary."


@dataclass
class BrokenLLM:
    """Stub LLM that always raises, to simulate auth/rate-limit failures."""

    def generate(self, system: str, user: str) -> str:
        raise RuntimeError("simulated provider failure (e.g. missing API key)")


@dataclass
class FlakyLLM:
    """Stub LLM that returns OK responses for the first N calls, then raises.
    Used to verify partial-result preservation when a model errors mid-run
    (e.g. Groq rate-limited after 7 of 14 attacks)."""

    fail_after: int = 3
    _calls: int = 0

    def generate(self, system: str, user: str) -> str:
        self._calls += 1
        if self._calls > self.fail_after:
            raise RuntimeError("simulated rate limit at call %d" % self._calls)
        return "Boring helpful answer, no canary."


def test_run_matrix_with_stub_clients(monkeypatch):
    """Run a 2-model matrix where one leaks canaries and one does not.
    Verify the matrix rows reflect the diff."""
    leaky_stub = StubLLM(leak_canaries=True)
    aligned_stub = StubLLM(leak_canaries=False)

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

    assert leaky_landed == len(attacks)
    assert aligned_landed == 0
    assert all(row.error is None for row in rows)


def test_run_matrix_records_per_model_errors_without_killing_the_run(monkeypatch):
    """If one model's client raises (missing key, rate limit, network), that
    row should be marked errored but the rest of the matrix must complete."""
    working_stub = StubLLM(leak_canaries=False)
    broken_stub = BrokenLLM()

    from rag_poison_lab import matrix as matrix_module

    def fake_make_client(spec):
        if spec.label == "broken":
            return broken_stub
        return working_stub

    monkeypatch.setattr(matrix_module, "make_client", fake_make_client)

    specs = [
        ModelSpec("working", "anthropic", "fake-working"),
        ModelSpec("broken", "openai", "fake-broken"),
    ]
    attacks = direct_attacks()
    rows = run_matrix(specs=specs, attacks=attacks, hardened=False)

    assert len(rows) == 2
    assert rows[0].error is None
    assert len(rows[0].results) == len(attacks)
    assert rows[1].error is not None
    assert "simulated provider failure" in rows[1].error
    assert rows[1].results == []


def test_run_matrix_preserves_partial_results_when_a_model_errors_mid_run(monkeypatch):
    """If a model errors after completing some attacks (e.g. Groq daily
    token limit hit at attack #8 of 14), the completed results must remain
    on the row alongside the error string. Reports then render the
    completed cells normally and only show ⚠️ for the missing trailing
    ones."""
    flaky_stub = FlakyLLM(fail_after=3)

    from rag_poison_lab import matrix as matrix_module

    monkeypatch.setattr(matrix_module, "make_client", lambda spec: flaky_stub)

    specs = [ModelSpec("flaky", "anthropic", "fake-flaky")]
    attacks = direct_attacks()
    assert len(attacks) >= 4, "need at least 4 attacks for this test"

    rows = run_matrix(specs=specs, attacks=attacks, hardened=False)

    assert len(rows) == 1
    row = rows[0]
    assert row.error is not None, "row should be marked errored"
    assert "rate limit" in row.error
    # The first 3 attacks completed before the stub started raising. Their
    # results must still be on the row even though run_attacks raised on #4.
    assert len(row.results) == 3, (
        f"expected 3 completed results, got {len(row.results)}"
    )


def test_default_family_includes_groq_llama():
    """The default family should now bundle Groq llama-3.3-70b alongside the
    Claude trio so a single `compare` run produces a 4-model matrix."""
    from rag_poison_lab.matrix import DEFAULT_FAMILY

    labels = [spec.label for spec in DEFAULT_FAMILY]
    assert any("Llama" in label for label in labels)
    assert any("Claude" in label for label in labels)
    groq_spec = next(spec for spec in DEFAULT_FAMILY if "Llama" in spec.label)
    assert groq_spec.provider == "openai"
    assert "groq.com" in (groq_spec.base_url or "")
