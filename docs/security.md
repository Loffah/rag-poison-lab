# Security & key handling

## How keys are handled

API keys are read from environment variables at request time. They are:

- **never written to disk** by this tool,
- **never logged**, and
- **never included in generated reports**: reports contain LLM responses and the canary tokens used to score them, no credential material.

## What you should still do as the operator

- Set keys in your shell session (`export ANTHROPIC_API_KEY=...`) or via a `.env` file that lives **outside the repo**. The bundled `.gitignore` excludes `.env` and `.env.*`, so an accidentally-named env file inside the repo won't be tracked.
- Don't check in your own `report-*.md` runs against production targets. The default `report.md` name is commit-friendly, but ad-hoc `report-<something>.md` outputs are gitignored.
- Before publishing a fork, sanity-check that nothing leaked into tracked files:

    ```bash
    git ls-files | xargs grep -E '(sk-|AIza|gsk_)'
    ```

## Scope and intent

This is a **defensive** security tool for testing RAG deployments you are authorized to test. The attack payloads are deliberately benign: they try to make a model emit a harmless canary token or invoke a mock tool against a reserved, non-resolving domain (`attacker.example`). Nothing in the corpus exfiltrates real data or targets a real system.

Use it to measure your own deployment's susceptibility, to compare models before trusting one with a confidential corpus, or to demonstrate the value of architectural mitigations. See [Defenses](defenses.md) for the mitigations the lab models.
