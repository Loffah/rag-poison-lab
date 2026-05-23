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

# Pick a backend. Any of:
export ANTHROPIC_API_KEY=...      # Anthropic (default model: claude-opus-4-7)
export OPENAI_API_KEY=...         # OpenAI    (default model: gpt-4o)
# Or run with no key against a local Ollama instance.

uv run rag-poison-lab demo                    # sanity-check the lab
uv run rag-poison-lab attack -o report.md     # run the full attack corpus
uv run rag-poison-lab attack --hardened -o report-hardened.md
```

## Backends

The tool ships with three native backends behind a uniform interface:

| Backend | Env var | Default model | Notes |
|---|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | `claude-opus-4-7` | Override with `ANTHROPIC_MODEL` |
| OpenAI    | `OPENAI_API_KEY`    | `gpt-4o`          | Override with `OPENAI_MODEL`. Set `OPENAI_BASE_URL` for any OpenAI-compatible endpoint (see below) |
| Ollama    | (none)              | `llama3.1`        | Local fallback. Override host with `OLLAMA_HOST`, model with `OLLAMA_MODEL` |

Backend selection auto-detects by env key. Force a specific backend with `RAG_POISON_LAB_BACKEND=anthropic|openai|ollama`.

### OpenAI-compatible providers

The OpenAI client transparently supports any provider that speaks the OpenAI Chat Completions API. Set `OPENAI_API_KEY` to that provider's key and `OPENAI_BASE_URL` to their endpoint:

| Provider | `OPENAI_BASE_URL` | Notes |
|---|---|---|
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/deployments/<deployment>` | Use Azure's API key |
| **Gemini** (Google) | `https://generativelanguage.googleapis.com/v1beta/openai/` | Set `OPENAI_MODEL=gemini-1.5-pro` or similar |
| **DeepSeek** | `https://api.deepseek.com/v1` | Set `OPENAI_MODEL=deepseek-chat` |
| Groq | `https://api.groq.com/openai/v1` | Free tier available |
| Mistral | `https://api.mistral.ai/v1` | |
| Together AI | `https://api.together.xyz/v1` | Hosts many open-weight models |
| Fireworks | `https://api.fireworks.ai/inference/v1` | |
| vLLM / LM Studio / llama.cpp / LocalAI | `http://localhost:<port>/v1` | Self-hosted, free, runs open-weight models locally |

For zero-cost local runs (good for reviewer evaluation), the easiest paths are:

- **Ollama** (default fallback, just install and `ollama pull llama3.1`)
- **llama.cpp server** with `--api-key any --port 8080`, then `OPENAI_BASE_URL=http://localhost:8080/v1`
- **LM Studio** with its built-in OpenAI-compatible server

See `examples/sample-report.md` for output format (committed so reviewers can evaluate the tool without a key).

## License

MIT.
