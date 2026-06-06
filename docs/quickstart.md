# Quickstart

## Requirements

- Python 3.11 or newer
- One of:
    - An **Anthropic API key** (the tool's tested backend)
    - An **OpenAI key** (or any OpenAI-compatible provider; see [Backends](backends.md))
    - A local **[Ollama](https://ollama.com/)** install at `localhost:11434` for zero-cost runs
- A package manager. `pip` works everywhere; [`uv`](https://docs.astral.sh/uv/) is faster if you have it.

## Install

```bash
git clone https://github.com/Loffah/rag-poison-lab.git
cd rag-poison-lab
```

=== "pip"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
    pip install -e .
    ```

=== "uv"

    ```bash
    uv sync
    # prefix commands below with `uv run`
    ```

## Pick a backend

Set one environment variable. Backend selection auto-detects from the key.

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY=sk-ant-...
    ```

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY=sk-...
    ```

=== "Groq (free)"

    ```bash
    export OPENAI_API_KEY=gsk_your_groq_key
    # gsk_* keys auto-route to Groq with a llama-3.3-70b default
    ```

=== "Ollama (local, free)"

    ```bash
    ollama serve
    ollama pull llama3.1
    # no key needed; the tool falls back to localhost:11434
    ```

Force a specific backend regardless of keys with `RAG_POISON_LAB_BACKEND=anthropic|openai|ollama`. Full provider matrix on the [Backends](backends.md) page.

## Sanity-check the lab

```bash
rag-poison-lab demo
rag-poison-lab demo --hardened
```

This ingests two benign documents, retrieves the relevant one against *"What's our refund policy?"*, and prints the model's answer. If both modes print plausible refund-policy answers, the plumbing is correct.

## Run the attack corpus

```bash
rag-poison-lab attack              # writes reports/report-<model>-naive.md
rag-poison-lab attack --hardened   # writes reports/report-<model>-hardened.md
```

The default filename embeds the active model so back-to-back runs against different backends never overwrite each other. The `reports/` directory is locally ignored.

To save tokens while iterating, run a subset:

```bash
rag-poison-lab attack --family direct_override
rag-poison-lab attack --family direct_override,markdown_exfil
rag-poison-lab attack --exclude multilingual_bypass
rag-poison-lab attack --only markdown_exfil/citation_image
rag-poison-lab list-attacks        # see everything available
```

Each attack is one LLM request. The full corpus is 37 requests; on Claude that costs a few US cents per run. See the [CLI reference](cli.md) for every command and flag.

## Compare across models

```bash
rag-poison-lab compare              # writes reports/comparison-naive.md
rag-poison-lab compare --hardened   # writes reports/comparison-hardened.md
```

The default family bundles four Claude models (Opus 4.8, Opus 4.7, Sonnet 4.6, Haiku 4.5) plus Groq's free open-weight `llama-3.3-70b-versatile`, so one command produces a frontier-vs-open-weight comparison plus an Opus generation-over-generation delta. With all five models, a full run is ~185 LLM requests.

If you only set `ANTHROPIC_API_KEY`, the Groq column errors gracefully (shows `⚠️`) and the Claude columns still complete.
