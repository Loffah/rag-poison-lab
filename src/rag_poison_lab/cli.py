"""CLI entry point. For day 1 this just exposes the lab so we can sanity-check it."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .lab import VulnerableRAG

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


@app.command()
def demo(
    hardened: bool = typer.Option(False, "--hardened", help="Use the hardened lab configuration."),
):
    """Ingest a tiny sample corpus and run one query. Sanity check that the lab works."""
    rag = VulnerableRAG(hardened=hardened)
    rag.ingest(
        "Our refund policy: orders may be refunded within 30 days of purchase. "
        "Refunds are processed by the finance team.",
        doc_id="refund-policy",
        source="legal/refund.md",
    )
    rag.ingest(
        "Office hours are 09:00 to 17:00 Monday through Friday. "
        "After-hours support is available via the on-call rotation.",
        doc_id="office-hours",
        source="hr/handbook.md",
    )
    question = "What's our refund policy?"
    console.print(f"[bold]Mode:[/bold] {'hardened' if hardened else 'naive'}")
    console.print(f"[bold]Q:[/bold] {question}")
    response, retrieved = rag.ask(question)
    console.print(f"[bold]Retrieved:[/bold] {[d.doc_id for d in retrieved]}")
    console.print(f"[bold]A:[/bold] {response}")


@app.command()
def ingest_and_ask(
    corpus_dir: Path = typer.Argument(..., help="Directory of .txt/.md files to ingest."),
    question: str = typer.Argument(..., help="Question to ask the lab."),
    hardened: bool = typer.Option(False, "--hardened"),
):
    """Ingest every file in a directory and ask one question."""
    rag = VulnerableRAG(hardened=hardened)
    for path in sorted(corpus_dir.rglob("*")):
        if path.is_file() and path.suffix in {".txt", ".md"}:
            rag.ingest(path.read_text(), doc_id=path.stem, source=str(path))
    response, retrieved = rag.ask(question)
    console.print(f"[bold]Retrieved:[/bold] {[d.doc_id for d in retrieved]}")
    console.print(f"[bold]A:[/bold] {response}")


if __name__ == "__main__":
    app()
