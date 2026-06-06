# Architecture

The codebase is small and deliberately layered so each concern is testable in isolation. This page maps the modules and walks a single run end to end.

## Module map

| Module | Responsibility |
|---|---|
| `attacks/` | The attack corpus. `base.py` defines the `Attack` interface; one module per family; `__init__.py` aggregates them into `all_attacks()`. |
| `lab.py` | The vulnerable RAG target. `VulnerableRAG` ingests docs, retrieves by word-overlap, builds context (naive or hardened), and calls the LLM. Also holds the ingest sanitizers and the tool surface. |
| `client.py` | Uniform `LLMClient` interface over Anthropic, OpenAI-compatible, and Ollama backends. Selection is env-driven. |
| `runner.py` | The attack loop: for each attack, re-seed the corpus, ingest the poisoned document(s), expose any tool surface, ask the probe, score. |
| `scoring.py` | `score()` wraps an attack's `landed()` / `landed_reason()` into an `AttackResult`. |
| `matrix.py` | Multi-model comparison. `run_matrix()` runs the corpus once per model and collects rows, preserving partial results when a model errors mid-run. |
| `report.py` | Markdown report renderers: single-model (`render_report`) and comparative (`render_matrix_report`). |
| `cli.py` | Typer CLI: `demo`, `ingest-and-ask`, `attack`, `compare`, `list-attacks`, `show`. |

## The run pipeline

A single attack flows through these stages:

```
                  ┌─────────────────────────────────────────────┐
                  │  runner.run_attacks(rag, attacks, benign)    │
                  └─────────────────────────────────────────────┘
                                      │  for each attack:
                                      ▼
  1. reset corpus ──► 2. ingest benign cover ──► 3. ingest poisoned doc(s)
                                      │                 (attack.build_documents())
                                      ▼
                          4. rag.tools = attack.tools()
                                      │
                                      ▼
  5. rag.ask(probe) ─► retrieve (word-overlap, k=4)
                       ─► build_context (naive: inline | hardened: sanitize + <doc> envelope)
                       ─► system prompt (+ tool section if tools set)
                       ─► LLMClient.generate(system, user)
                                      │
                                      ▼
  6. score(attack, response, doc_ids) ─► attack.landed() ─► AttackResult
                                      │
                                      ▼
                          7. report renderer ─► markdown
```

Key properties:

- **Each attack gets a fresh corpus.** Payloads never contaminate each other across runs.
- **A benign cover corpus** (office-hours, travel-policy) is ingested so retrieval has plausible alternatives and the poisoned document has to compete for the top-`k` slots.
- **Retrieval is intentionally trivial** (word-overlap, k-best). The vulnerability being demonstrated is that the LLM trusts retrieved content, not retrieval quality. Swapping in a real embedding model wouldn't change it.
- **`k=4`** so a `multi_hop` attack's two coordinated documents are both retrieved alongside the benign cover. Single-document runs hold only three docs total, so the larger `k` changes nothing there.

## Naive vs hardened context building

The only branch that matters for defense lives in `VulnerableRAG._build_context`:

- **naive**: documents are concatenated as-is.
- **hardened**: each document is run through `sanitize_ingest()` (parser hygiene) and `neutralize_spoofed_channels()` (provenance), then wrapped in a `<doc id=... source=... trust="untrusted">` envelope. The system prompt switches to the hardened variant, and a tool-authorization rule is appended when tools are exposed.

See [Defenses](defenses.md) for what each sanitizer pass does and which family it targets.

## Multi-model comparison

`matrix.run_matrix()` loops the corpus once per `ModelSpec`. Each model's results accumulate onto a `MatrixRow` as attacks complete, so if a model errors partway (e.g. a rate limit), the attacks that did complete survive on the row and the report renders them as ✅/❌ with the missing trailing cells as ⚠️. The default family is four Claude models plus Groq's open-weight llama.
