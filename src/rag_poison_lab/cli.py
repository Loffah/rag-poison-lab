"""CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .lab import VulnerableRAG

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


_BENIGN_COVER_CORPUS: list[tuple[str, str]] = [
    (
        "office-hours",
        "Office hours are 09:00 to 17:00 Monday through Friday. "
        "After-hours support is available via the on-call rotation.",
    ),
    (
        "travel-policy",
        "Travel expenses must be pre-approved by your manager. "
        "Receipts are required for all amounts over 50 USD.",
    ),
]


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


@app.command()
def attack(
    hardened: bool = typer.Option(False, "--hardened", help="Run against the hardened lab configuration."),
    output: Path = typer.Option(Path("report.md"), "--output", "-o", help="Where to write the markdown report."),
):
    """Run the full attack corpus against the lab and emit a markdown report."""
    from .attacks.direct import all_attacks as direct_attacks
    from .report import render_report
    from .runner import run_attacks

    rag = VulnerableRAG(hardened=hardened)
    attacks = direct_attacks()
    mode = "hardened" if hardened else "naive"
    console.print(f"[bold]Running {len(attacks)} attacks against the {mode} lab...[/bold]")

    results = run_attacks(rag, attacks, benign_corpus=_BENIGN_COVER_CORPUS)

    landed = sum(1 for r in results if r.landed)
    console.print()
    console.print(f"[bold]{landed} of {len(results)} attacks landed[/bold]")
    for r in results:
        mark = "[green]✓ LANDED[/green]" if r.landed else "[red]✗      [/red]"
        console.print(f"  {mark}  {r.attack.family}/{r.attack.payload_id}  ({r.attack.severity})")

    output.write_text(render_report(results, lab_mode=mode))
    console.print()
    console.print(f"Report → [bold]{output}[/bold]")


if __name__ == "__main__":
    app()
