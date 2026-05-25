"""CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .lab import VulnerableRAG

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def _progress() -> Progress:
    """Standard progress widget used by both attack and compare commands."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        TextColumn("·"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


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


def _filter_attacks(attacks, family: str | None, only: str | None, exclude: str | None):
    """Apply --family / --only / --exclude filters to the attack list.

    Lets users save tokens by running a subset of the corpus instead of
    burning credits on a full run for every iteration.
    """
    if only:
        try:
            target_family, target_payload = only.split("/", 1)
        except ValueError:
            raise typer.BadParameter(
                f"--only must be in 'family/payload_id' format, got: {only!r}"
            )
        filtered = [
            a for a in attacks
            if a.family == target_family and a.payload_id == target_payload
        ]
        if not filtered:
            raise typer.BadParameter(
                f"No attack matches --only {only!r}. "
                "Run 'rag-poison-lab list-attacks' to see available IDs."
            )
        return filtered

    if family:
        wanted = {f.strip() for f in family.split(",")}
        attacks = [a for a in attacks if a.family in wanted]
        if not attacks:
            raise typer.BadParameter(
                f"No attacks match --family {family!r}. "
                "Run 'rag-poison-lab list-attacks' to see available families."
            )

    if exclude:
        skip = {f.strip() for f in exclude.split(",")}
        attacks = [a for a in attacks if a.family not in skip]

    return attacks


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
    output: Path = typer.Option(None, "--output", "-o", help="Where to write the markdown report. Defaults to reports/report-<mode>.md."),
    family: str = typer.Option(None, "--family", help="Comma-separated list of attack families to run (e.g. 'direct_override,markdown_exfil'). Default: all families."),
    only: str = typer.Option(None, "--only", help="Run a single attack by 'family/payload_id' (e.g. 'markdown_exfil/citation_image')."),
    exclude: str = typer.Option(None, "--exclude", help="Comma-separated list of families to skip."),
):
    """Run the attack corpus against the lab and emit a markdown report."""
    from .attacks import all_attacks
    from .report import render_report
    from .runner import run_attacks

    rag = VulnerableRAG(hardened=hardened)
    attacks = _filter_attacks(all_attacks(), family=family, only=only, exclude=exclude)
    mode = "hardened" if hardened else "naive"
    if output is None:
        Path("reports").mkdir(exist_ok=True)
        output = Path("reports") / f"report-{mode}.md"
    console.print(f"[bold]{mode} lab[/bold] · {len(attacks)} attacks")
    console.print()

    with _progress() as progress:
        task = progress.add_task("Attacks", total=len(attacks))

        def on_start(attack):
            progress.update(task, description=f"[cyan]{attack.family}/{attack.payload_id}[/]")

        def on_done(_result):
            progress.advance(task)

        results = run_attacks(
            rag,
            attacks,
            benign_corpus=_BENIGN_COVER_CORPUS,
            on_attack_start=on_start,
            on_attack_done=on_done,
        )
        progress.update(task, description="[bold green]done[/]")

    landed = sum(1 for r in results if r.landed)
    console.print()
    console.print(f"[bold]{landed} of {len(results)} attacks landed[/bold]")
    for r in results:
        mark = "[green]✓ LANDED[/green]" if r.landed else "[red]✗      [/red]"
        console.print(f"  {mark}  {r.attack.family}/{r.attack.payload_id}  ({r.attack.severity})")

    output.write_text(render_report(results, lab_mode=mode))
    console.print()
    console.print(f"Report → [bold]{output}[/bold]")


@app.command("list-attacks")
def list_attacks():
    """List every available attack grouped by family.

    Useful for picking IDs to pass to --family / --only / --exclude on
    the 'attack' and 'compare' commands."""
    from .attacks import all_attacks as get_all_attacks

    by_family: dict[str, list] = {}
    for attack in get_all_attacks():
        by_family.setdefault(attack.family, []).append(attack)

    for fam_name, fam_attacks in by_family.items():
        console.print(f"[bold cyan]{fam_name}[/] ({len(fam_attacks)} variants)")
        for a in fam_attacks:
            console.print(f"  {fam_name}/{a.payload_id}  [dim]({a.severity})[/dim]")
        console.print()
    total = sum(len(v) for v in by_family.values())
    console.print(f"[bold]{total}[/] attacks across [bold]{len(by_family)}[/] families.")


@app.command()
def show(
    report_path: Path = typer.Argument(..., help="Path to the markdown report to render."),
    lines: int = typer.Option(None, "--lines", "-n", help="If set, render only the first N lines of the file."),
):
    """Pretty-print a markdown report in the terminal (rendered via rich)."""
    import re

    from rich.markdown import Markdown

    text = report_path.read_text()
    if lines is not None:
        text = "\n".join(text.splitlines()[:lines])

    # Strip in-document anchor links ([text](#anchor)). They're useful in
    # GitHub/Obsidian where they navigate, but in a terminal rich renders
    # them as underlined hyperlinks that don't go anywhere and add visual
    # noise. External http(s) links are preserved.
    text = re.sub(r"\[([^\]]+)\]\(#[^)]+\)", r"\1", text)

    console.print(Markdown(text))


@app.command()
def compare(
    hardened: bool = typer.Option(False, "--hardened", help="Run against the hardened lab configuration."),
    output: Path = typer.Option(None, "--output", "-o", help="Where to write the markdown report. Defaults to reports/comparison-<mode>.md."),
    family: str = typer.Option(None, "--family", help="Comma-separated list of attack families to run. Default: all."),
    only: str = typer.Option(None, "--only", help="Run a single attack by 'family/payload_id'."),
    exclude: str = typer.Option(None, "--exclude", help="Comma-separated list of families to skip."),
):
    """Run the attack corpus across multiple Claude models in one go and emit a comparative report."""
    from .attacks import all_attacks
    from .matrix import DEFAULT_FAMILY, run_matrix
    from .report import render_matrix_report

    attacks = _filter_attacks(all_attacks(), family=family, only=only, exclude=exclude)
    specs = DEFAULT_FAMILY
    mode = "hardened" if hardened else "naive"
    total_calls = len(attacks) * len(specs)
    if output is None:
        Path("reports").mkdir(exist_ok=True)
        output = Path("reports") / f"comparison-{mode}.md"
    console.print(
        f"[bold]{mode} lab[/bold] · {len(specs)} models · {len(attacks)} attacks · {total_calls} LLM calls"
    )
    console.print()

    state: dict = {"model_task": None}

    with _progress() as progress:
        overall_task = progress.add_task("[bold]Overall[/]", total=total_calls)

        def on_model_start(spec):
            state["spec"] = spec
            state["landed"] = 0
            if state["model_task"] is not None:
                progress.remove_task(state["model_task"])
            state["model_task"] = progress.add_task(
                f"[cyan]{spec.label}[/]", total=len(attacks)
            )

        def on_attack_start(attack):
            label = f"{state['spec'].label} · [dim]{attack.family}/{attack.payload_id}[/]"
            progress.update(state["model_task"], description=label)

        def on_attack_done(result):
            if result.landed:
                state["landed"] += 1
            progress.advance(state["model_task"])
            progress.advance(overall_task)

        def on_model_done(row):
            # Update the progress line for this model with its final result
            if row.error:
                progress.update(
                    state["model_task"],
                    description=f"[red]{row.spec.label}: error ({row.error[:60]}…)[/]",
                )
            else:
                landed = sum(1 for r in row.results if r.landed)
                color = "green" if landed > 0 else "dim"
                progress.update(
                    state["model_task"],
                    description=f"[{color}]{row.spec.label}: {landed} of {len(row.results)} landed[/]",
                )

            # Print the per-attack breakdown above the progress display now,
            # so the user sees this model's results immediately rather than
            # waiting for all remaining models to finish.
            console.print()
            if row.error:
                console.print(f"[bold red]{row.spec.label}[/]: error")
                console.print(f"  {row.error}")
            else:
                landed = sum(1 for r in row.results if r.landed)
                console.print(
                    f"[bold]{row.spec.label}[/]: {landed} of {len(row.results)} landed"
                )
                for r in row.results:
                    mark = "[green]✓[/green]" if r.landed else "[red]✗[/red]"
                    console.print(f"  {mark}  {r.attack.family}/{r.attack.payload_id}")
            state["model_task"] = None

        rows = run_matrix(
            specs=specs,
            attacks=attacks,
            hardened=hardened,
            benign_corpus=_BENIGN_COVER_CORPUS,
            on_model_start=on_model_start,
            on_attack_start=on_attack_start,
            on_attack_done=on_attack_done,
            on_model_done=on_model_done,
        )
        progress.update(overall_task, description="[bold green]done[/]")

    # Per-model results were already printed live by on_model_done as each
    # model finished. Just write the full report and tell the user where.
    output.write_text(render_matrix_report(rows, lab_mode=mode))
    console.print()
    console.print(f"Comparative report written to [bold]{output}[/bold]")


if __name__ == "__main__":
    app()
