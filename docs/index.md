# rag-poison-lab

Plant text in a **RAG (Retrieval-Augmented Generation)** system's documents and you can hijack the agent that reads them. **rag-poison-lab** is a pentest harness that measures how susceptible a model actually is: a curated 37-attack corpus across 8 indirect-injection families, scored deterministically with canary tokens, compared across models and naive-vs-hardened defenses.

!!! warning "Status: under active development"
    This is a working research tool, not a finished product. Interfaces and the attack corpus change between commits.

## What this does

RAG systems pull documents into LLM context to answer user questions. The LLM treats those documents as trusted context. If an attacker can plant content in the corpus (via a supplier portal, a parsed email, a scraped web source), they can inject instructions the model will follow.

This tool tests for that. It ships with:

1. A **self-contained vulnerable RAG lab** so you can run attacks against a controllable target without needing a real system.
2. **Eight attack families** (37 attacks total) spanning model alignment, the chat-UI renderer, the document parser, the document trust model, the retrieval system, and the agent's tool surface. See [Attack families](attack-families.md).
3. **Family-aware scoring** that detects landings deterministically: a unique canary token per attack, with stricter structural rules where a bare substring match would over-count (image syntax for exfil, `CALL` syntax for tool hijack). See [Scoring](scoring.md).
4. **Markdown reports** with an executive summary, a landing matrix, expanded landings, and collapsed defeats, suitable for a pentest deliverable.
5. **Multi-model comparison** (`compare`) that runs the corpus across several models in one invocation and emits a side-by-side matrix.
6. A **naive vs hardened toggle** so you can measure which attack families survive proper architectural defenses. See [Defenses](defenses.md).

## The threat model

The threat model is simple: **if you can plant text in someone's ingestion path, you can try to hijack their agent.** Enterprises are deploying RAG over confidential corpora (operations data, contracts, internal docs), and the defenses are uneven across models. The variance is what defenders need to measure when they pick a model to trust with a confidential corpus.

## A note on framing

The frontier Claude models defeat most attacks in the current corpus most of the time. They actively recognize the patterns and refuse, often explaining the attempt to the user. They are not airtight, and weaker or open-weight models are far more susceptible. The tool's primary value is **comparative measurement**: same corpus, multiple models, multiple lab configurations. The deltas (frontier vs open-weight, generation-over-generation, naive vs hardened) are what matter.

!!! note "Landings are probabilistic"
    Model behavior varies between runs, so the same attack against the same model can land in one run and be defeated in the next. The matrix in any single report is one sample of that distribution. Draw conclusions about a model's susceptibility from multiple runs, not a single matrix.

## Where to go next

- **[Quickstart](quickstart.md)**: install, pick a backend, run the corpus.
- **[Attack families](attack-families.md)**: the full inventory and the architectural layer each one exploits.
- **[Architecture](architecture.md)**: how a run flows from corpus to report.
- **[Writing an attack](extending.md)**: add your own family.
