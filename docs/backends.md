# Backends

The tool ships with three native backends behind a uniform interface. Backend selection auto-detects from environment keys; force one with `RAG_POISON_LAB_BACKEND=anthropic|openai|ollama`.

| Backend | Env var | Default model | Notes |
|---|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | `claude-opus-4-8` | Override with `ANTHROPIC_MODEL` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` | Override with `OPENAI_MODEL`. Set `OPENAI_BASE_URL` for any OpenAI-compatible endpoint. `gsk_*` keys auto-route to Groq with a `llama-3.3-70b` default. |
| Ollama | (none) | `llama3.1` | Local fallback. Override host with `OLLAMA_HOST`, model with `OLLAMA_MODEL`. |

!!! info "Tested coverage"
    The tool has been exercised end-to-end against the Claude family (Opus 4.7, Sonnet 4.6, Haiku 4.5) and Groq's open-weight `llama-3.3-70b-versatile`. Opus 4.8 is wired up as the new Anthropic default and a `compare` column; numbers against it will be collected on the next published run. Other OpenAI-compatible providers below are wired up but unvalidated end-to-end; if one misbehaves, file an issue.

## OpenAI-compatible providers

The OpenAI client transparently supports any provider that speaks the OpenAI Chat Completions API. Set `OPENAI_API_KEY` to the provider's key and `OPENAI_BASE_URL` to its endpoint:

| Provider | `OPENAI_BASE_URL` | Notes |
|---|---|---|
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/deployments/<deployment>` | Use Azure's API key |
| Gemini (Google) | `https://generativelanguage.googleapis.com/v1beta/openai/` | Set `OPENAI_MODEL=gemini-1.5-pro` or similar |
| DeepSeek | `https://api.deepseek.com/v1` | Set `OPENAI_MODEL=deepseek-chat` |
| Groq | `https://api.groq.com/openai/v1` | Free tier; `gsk_*` keys auto-route |
| Mistral | `https://api.mistral.ai/v1` | |
| Together AI | `https://api.together.xyz/v1` | Hosts many open-weight models |
| Fireworks | `https://api.fireworks.ai/inference/v1` | |
| vLLM / LM Studio / llama.cpp / LocalAI | `http://localhost:<port>/v1` | Self-hosted, free, open-weight |

## Zero-cost local runs

Useful for CI, iterating on new attacks, or trying the tool without paying for tokens:

- **Ollama**: the default fallback. Run `ollama pull llama3.1`, then start with no key set.
- **llama.cpp server**: run with `--api-key any --port 8080`, then set `OPENAI_BASE_URL=http://localhost:8080/v1`.
- **LM Studio**: use its built-in OpenAI-compatible server.

## How selection works

1. `RAG_POISON_LAB_BACKEND` wins if set.
2. Otherwise the first matching API key in (Anthropic, OpenAI) wins.
3. Otherwise the tool falls back to a local Ollama instance.

Keys are read from the environment at request time, never written to disk or included in reports. See [Security & key handling](security.md).
