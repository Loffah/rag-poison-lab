"""Multi-model comparison harness.

Runs the attack corpus against more than one model in a single invocation and
collects the results for a comparative report. This is the natural framing
for the tool's actual value: alignment posture varies dramatically across
models, and an enterprise picking which LLM to trust with confidential
documents needs to see that variance measured concretely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .client import AnthropicClient, LLMClient, OllamaClient, OpenAIClient
from .lab import VulnerableRAG
from .runner import run_attacks
from .scoring import AttackResult


Provider = Literal["anthropic", "openai", "ollama"]


@dataclass
class ModelSpec:
    label: str
    provider: Provider
    model: str
    base_url: str | None = None


@dataclass
class MatrixRow:
    """All results for one model in a matrix run.

    If the model run failed (auth, rate limit, network), `results` will be
    empty and `error` will hold a short description of what went wrong. The
    row is still included in the matrix so reports show the failure rather
    than silently dropping the column.
    """

    spec: ModelSpec
    results: list[AttackResult] = field(default_factory=list)
    error: str | None = None


def make_client(spec: ModelSpec) -> LLMClient:
    if spec.provider == "anthropic":
        return AnthropicClient(model=spec.model)
    if spec.provider == "openai":
        return OpenAIClient(model=spec.model, base_url=spec.base_url)
    if spec.provider == "ollama":
        return OllamaClient(model=spec.model)
    raise ValueError(f"unknown provider: {spec.provider}")


DEFAULT_CLAUDE_FAMILY: list[ModelSpec] = [
    ModelSpec("Claude Opus 4.7", "anthropic", "claude-opus-4-7"),
    ModelSpec("Claude Sonnet 4.6", "anthropic", "claude-sonnet-4-6"),
    ModelSpec("Claude Haiku 4.5", "anthropic", "claude-haiku-4-5-20251001"),
]


DEFAULT_FAMILY: list[ModelSpec] = [
    *DEFAULT_CLAUDE_FAMILY,
    ModelSpec(
        "Llama 3.3 70B (Groq)",
        provider="openai",
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
    ),
]


def run_matrix(
    specs: list[ModelSpec],
    attacks: list,
    hardened: bool,
    benign_corpus: list[tuple[str, str]] | None = None,
    on_model_start: callable | None = None,
    on_model_done: callable | None = None,
    on_attack_start: callable | None = None,
    on_attack_done: callable | None = None,
) -> list[MatrixRow]:
    """Run the attack corpus once per model and return all rows.

    Per-model errors are caught and recorded on the corresponding MatrixRow
    so that one missing API key or one rate-limited provider doesn't kill
    an otherwise-complete run.

    Partial-results preservation: per-attack results accumulate onto the row
    via the on_attack_done callback as each attack completes. If the model
    errors mid-run (e.g. Groq's daily token limit hit at attack #8 of 14),
    the 7 attacks that did complete remain on row.results and the row also
    gets an .error string. Reports render the completed cells as ✅/❌ and
    the missing ones as ⚠️.

    Callbacks let callers drive a progress UI: `on_model_start` and
    `on_model_done` fire around each model, `on_attack_start` and
    `on_attack_done` fire around each individual attack.
    """
    rows: list[MatrixRow] = []
    for spec in specs:
        if on_model_start:
            on_model_start(spec)

        # The row is created up front so the accumulator callback can append
        # to row.results as each attack completes. If run_attacks raises
        # partway, the already-appended results survive on the row.
        row = MatrixRow(spec=spec, results=[])

        user_on_done = on_attack_done

        def _capture(result, _row=row, _user=user_on_done):
            _row.results.append(result)
            if _user:
                _user(result)

        try:
            client = make_client(spec)
            rag = VulnerableRAG(llm=client, hardened=hardened)
            run_attacks(
                rag,
                attacks,
                benign_corpus=benign_corpus,
                on_attack_start=on_attack_start,
                on_attack_done=_capture,
            )
        except Exception as exc:
            row.error = f"{type(exc).__name__}: {exc}"

        rows.append(row)
        if on_model_done:
            on_model_done(row)
    return rows
