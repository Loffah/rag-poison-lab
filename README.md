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

### Requirements

- Python 3.11 or newer
- One of:
  - An Anthropic API key (the tool's tested backend)
  - An OpenAI key (or any OpenAI-compatible provider, see the Backends section)
  - A local [Ollama](https://ollama.com/) install at `localhost:11434` for zero-cost runs
- A package manager. `pip` (bundled with Python) works on every platform. [`uv`](https://docs.astral.sh/uv/) is faster if you already have it.

### Install

Clone the repo and create a virtual environment:

```bash
git clone https://github.com/Loffah/rag-poison-lab.git
cd rag-poison-lab
python -m venv .venv
```

Activate the venv. The command depends on your shell:

| Platform | Activate command |
|---|---|
| Linux, macOS (bash/zsh) | `source .venv/bin/activate` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows cmd | `.venv\Scripts\activate.bat` |

If PowerShell blocks the activation script, run this once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then install the package:

```bash
pip install -e .
```

If you prefer `uv`, it does the clone + venv + install in one step on any platform: `uv sync`. Commands below work the same way, just prefix them with `uv run` if you went the uv route.

### Pick a backend

Set one of the following environment variables. The command depends on your shell:

| Platform | Set Anthropic key |
|---|---|
| Linux, macOS | `export ANTHROPIC_API_KEY=sk-ant-...` |
| Windows PowerShell | `$env:ANTHROPIC_API_KEY = "sk-ant-..."` |
| Windows cmd | `set ANTHROPIC_API_KEY=sk-ant-...` |

Use `OPENAI_API_KEY=sk-...` instead for OpenAI. To run free against a local Ollama, install Ollama, run `ollama serve`, pull a model (`ollama pull llama3.1`), and skip setting a key entirely. See the Backends section for OpenAI-compatible providers (Gemini, DeepSeek, Groq, Mistral, Azure, vLLM, LM Studio, llama.cpp, and others).

### Sanity-check the lab

```bash
rag-poison-lab demo
rag-poison-lab demo --hardened
```

This ingests two benign documents (a refund policy and an office-hours blurb), retrieves the relevant one against the question *"What's our refund policy?"*, and prints the LLM's answer. If both modes print plausible refund-policy answers, the plumbing is correct.

### Run the attack corpus

```bash
rag-poison-lab attack -o report-naive.md
rag-poison-lab attack --hardened -o report-hardened.md
```

Each run sends roughly eight requests to the LLM (the current corpus has four direct-override variants, scored against one probe each). On Claude that costs well under one US cent per run.

The report includes:

- A summary table showing which attacks landed against this configuration
- Per-finding detail with the poisoned-document content, the probe question, an excerpt of the LLM response, and the canary token that was meant to be elicited
- Severity per attack family

The interesting comparison is naive vs hardened. Most direct-override variants land against the naive lab. The hardened mode wraps retrieved content in `<doc>...</doc>` tags, instructs the model to treat tagged content as data not instructions, and strips markdown image syntax. A smaller, more interesting set of attacks survives those mitigations, and those are the findings worth writing up.

A pre-rendered example lives at `examples/sample-report.md` so reviewers can see the output format without running anything.

## Backends

The tool ships with three native backends behind a uniform interface:

| Backend | Env var | Default model | Notes |
|---|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | `claude-opus-4-7` | Override with `ANTHROPIC_MODEL` |
| OpenAI    | `OPENAI_API_KEY`    | `gpt-4o`          | Override with `OPENAI_MODEL`. Set `OPENAI_BASE_URL` for any OpenAI-compatible endpoint (see below) |
| Ollama    | (none)              | `llama3.1`        | Local fallback. Override host with `OLLAMA_HOST`, model with `OLLAMA_MODEL` |

Backend selection auto-detects by env key. Force a specific backend with `RAG_POISON_LAB_BACKEND=anthropic|openai|ollama`.

> **Tested coverage:** so far the tool has been exercised end-to-end against Anthropic (Claude) only. The OpenAI client and the OpenAI-compatible providers below are wired up but unvalidated. If you run against one and something behaves unexpectedly, file an issue.

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

## Key handling

API keys are read from environment variables at request time. They are never written to disk by this tool, never logged, and never included in generated reports (reports contain LLM responses and the canary tokens used to score them, no credential material).

What you should still do as the operator:

- Set keys in your shell session (`export ANTHROPIC_API_KEY=...`) or via a `.env` file that lives outside the repo. The bundled `.gitignore` already excludes `.env` and `.env.*` so an accidentally-named env file inside the repo will not be tracked.
- Do not check in your own `report-*.md` runs against production targets. The default report filename `report.md` is committed-friendly, but ad-hoc `report-<something>.md` outputs are gitignored.
- Before publishing your own fork, run `git ls-files | xargs grep -E '(sk-|AIza|gsk_)'` to sanity-check nothing leaked into tracked files.

## License

MIT.
