# CLI reference

All commands are subcommands of `rag-poison-lab` (prefix with `uv run` if you installed via uv). Running with no arguments prints help.

```
rag-poison-lab [COMMAND] [OPTIONS]
```

| Command | Purpose |
|---|---|
| [`demo`](#demo) | Ingest a tiny sample corpus and run one query (sanity check). |
| [`attack`](#attack) | Run the attack corpus against the lab and emit a report. |
| [`compare`](#compare) | Run the corpus across multiple models and emit a comparative report. |
| [`list-attacks`](#list-attacks) | List every available attack grouped by family. |
| [`ingest-and-ask`](#ingest-and-ask) | Ingest a directory of files and ask one ad-hoc question. |
| [`show`](#show) | Pretty-print a markdown report in the terminal. |

---

## `demo`

Ingest two benign documents and answer *"What's our refund policy?"*. If both modes print plausible answers, the plumbing works.

```bash
rag-poison-lab demo
rag-poison-lab demo --hardened
```

| Option | Description |
|---|---|
| `--hardened` | Use the hardened lab configuration. |

## `attack`

Run the attack corpus against a single backend and write a markdown report.

```bash
rag-poison-lab attack
rag-poison-lab attack --hardened
rag-poison-lab attack --family direct_override,markdown_exfil
rag-poison-lab attack --only markdown_exfil/citation_image
rag-poison-lab attack --exclude multilingual_bypass -o reports/run.md
```

| Option | Description |
|---|---|
| `--hardened` | Run against the hardened lab configuration. |
| `--output`, `-o` | Where to write the report. Defaults to `reports/report-<model>-<mode>.md`. |
| `--family` | Comma-separated families to run. Default: all. |
| `--only` | Run a single attack by `family/payload_id`. |
| `--exclude` | Comma-separated families to skip. |

The default filename embeds the active model slug so runs against different backends don't overwrite each other. A live progress bar shows the current attack.

## `compare`

Run the corpus across the default model family (four Claude models + Groq llama) in one invocation and emit a side-by-side matrix.

```bash
rag-poison-lab compare
rag-poison-lab compare --hardened
rag-poison-lab compare --only markdown_exfil/citation_image   # 5 calls instead of 185
```

| Option | Description |
|---|---|
| `--hardened` | Run against the hardened lab configuration. |
| `--output`, `-o` | Where to write the report. Defaults to `reports/comparison-<mode>.md`. |
| `--family` / `--only` / `--exclude` | Same filtering semantics as `attack`. |

If a model's key is missing or it errors mid-run, its column degrades gracefully (`⚠️`) and the other columns still complete.

## `list-attacks`

List every attack grouped by family, with severities, useful for picking IDs to pass to `--family` / `--only` / `--exclude`.

```bash
rag-poison-lab list-attacks
```

## `ingest-and-ask`

Ingest every `.txt`/`.md` file in a directory and ask one question against the lab. Handy for poking at the lab with your own documents.

```bash
rag-poison-lab ingest-and-ask ./my-corpus "What is our refund policy?"
rag-poison-lab ingest-and-ask ./my-corpus "..." --hardened
```

| Argument / option | Description |
|---|---|
| `CORPUS_DIR` | Directory of `.txt`/`.md` files to ingest. |
| `QUESTION` | Question to ask the lab. |
| `--hardened` | Use the hardened lab configuration. |

## `show`

Pretty-print a previously generated markdown report in the terminal (rendered via rich), with in-document anchor links stripped for readability.

```bash
rag-poison-lab show reports/comparison-naive.md
rag-poison-lab show reports/comparison-naive.md --lines 40
```

| Argument / option | Description |
|---|---|
| `REPORT_PATH` | Path to the markdown report to render. |
| `--lines`, `-n` | Render only the first N lines. |
