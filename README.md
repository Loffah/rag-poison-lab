# rag-poison-lab

A pentest harness for RAG (Retrieval-Augmented Generation) systems. Probes a target RAG with a curated corpus of indirect prompt-injection attacks and reports which attack families succeed.

Status: under active development.

## What this does

RAG systems pull documents into LLM context to answer user questions. The LLM treats those documents as trusted context. If an attacker can plant content in the corpus (via a supplier portal, parsed email, scraped web source, etc.), they can inject instructions the model will follow.

This tool tests for that. It ships with:

1. A **self-contained vulnerable RAG lab** so you can run attacks against a controllable target without needing a real system.
2. An **attack corpus** covering: direct override, indirect injection via document content, hidden text, markdown-based exfiltration, multilingual guardrail bypass, and tool-call hijack.
3. **Canary-token scoring** to detect when attacks succeed deterministically.
4. **Markdown reports** suitable for inclusion in a pentest deliverable.
5. A **mitigations toggle** so you can compare naive vs hardened RAG configurations and see which attack families survive proper defenses.

## Why this exists

Enterprises are deploying RAG over confidential corpora (operations data, contracts, internal docs). The threat model is simple: if you can plant text in someone's ingestion path, you can hijack their agent. That surface is real but under-tested. This is a working tool to make it measurable.

## Quickstart

```bash
uv sync
export ANTHROPIC_API_KEY=...
uv run rag-poison-lab demo
```

Documentation is being filled in as the tool ships. See `examples/sample-report.md` for output format.

## License

MIT.
