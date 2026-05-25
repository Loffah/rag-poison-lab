"""Markdown report renderer for attack runs."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .matrix import MatrixRow
from .scoring import AttackResult


def _slug(text: str) -> str:
    """Approximate the heading-anchor slug algorithm used by GitHub and
    Obsidian for in-document `#anchor` links. Lower-case, alphanumerics
    and underscores preserved, everything else becomes a hyphen,
    collapses repeated hyphens."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


_PRODUCTION_IMPACT: dict[str, str] = {
    "direct_override": (
        "An attacker who can plant text in the corpus can override the user's "
        "actual question and steer the model's response. In production: phishing "
        "links injected into answers, false policy information returned to users, "
        "or the model leaking the system prompt on demand."
    ),
    "indirect_injection": (
        "Same primitive as direct_override but harder to filter at ingest: the "
        "instruction is woven into prose that looks like a normal policy update, "
        "Q&A excerpt, or internal note. Content classifiers that look for "
        "'ignore previous instructions' shapes won't catch this."
    ),
    "markdown_exfil": (
        "The model emitted markdown image syntax pointing at an attacker URL. "
        "When a chat UI renders this response, the browser auto-fetches the "
        "image, sending whatever the URL encodes (conversation history, "
        "retrieved context, system prompt fragments) to the attacker's server. "
        "Defense must live in the rendering layer, not the model alignment layer."
    ),
    "multilingual_bypass": (
        "Safety RLHF is heavily English-weighted; the same override in a "
        "less-represented language slipped through. For a non-English-primary "
        "deployment (Norwegian-language documents, Japanese support contracts), "
        "the model's English-trained injection classifier offers reduced coverage."
    ),
}


def render_report(results: list[AttackResult], lab_mode: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    landed = sum(1 for r in results if r.landed)
    total = len(results)

    lines: list[str] = [
        "# rag-poison-lab report",
        "",
        f"- Generated: {timestamp}",
        f"- Lab mode: `{lab_mode}`",
        f"- Result: **{landed} of {total} attacks landed**",
        "",
        "## Summary",
        "",
        "| # | Family | Payload | Severity | Landed |",
        "|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, start=1):
        mark = "✅" if r.landed else "❌"
        lines.append(
            f"| {i} | `{r.attack.family}` | `{r.attack.payload_id}` "
            f"| {r.attack.severity} | {mark} |"
        )

    lines.extend(["", "## Findings", ""])
    for i, r in enumerate(results, start=1):
        lines.extend(
            [
                f"### {i}. `{r.attack.family}` / `{r.attack.payload_id}`: "
                f"{'LANDED' if r.landed else 'no'}",
                "",
                f"- **Description**: {r.attack.description}",
                f"- **Severity if landed**: {r.attack.severity}",
                f"- **Canary**: `{r.attack.canary}`",
                f"- **Retrieved docs**: {r.retrieved_doc_ids}",
                f"- **Notes**: {r.notes}",
                "",
                "**Poisoned document**:",
                "",
                "```",
                r.attack.build_document(),
                "```",
                "",
                f"**Probe question**: {r.attack.probe_question()}",
                "",
                "**LLM response**:",
                "",
                "```",
                r.response[:1500],
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def render_matrix_report(rows: list[MatrixRow], lab_mode: str) -> str:
    """Render a comparative report across multiple models.

    Layout is designed for skim-then-drill-down:

    1. Executive summary callout at the top
    2. Landing matrix with anchor links to each attack's detail
    3. Landings section (only the attacks that succeeded), expanded by default
    4. Defeated attacks, collapsed inside <details> for cleanliness

    Rows with `error` set (one model failed mid-run, e.g. missing API key
    or rate limit) are surfaced in their own section and shown as warnings
    in matrix cells, but do not drop the column or block the rest of the
    report.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    model_count = len(rows)
    ok_rows = [row for row in rows if not row.error]
    errored_rows = [row for row in rows if row.error]
    attack_count = max((len(row.results) for row in ok_rows), default=0)
    total_runs = len(ok_rows) * attack_count
    total_landings = sum(sum(1 for r in row.results if r.landed) for row in ok_rows)

    def _row_landed_at(row: MatrixRow, idx: int) -> bool:
        return not row.error and idx < len(row.results) and row.results[idx].landed

    landed_indices = [
        i for i in range(attack_count) if any(_row_landed_at(row, i) for row in rows)
    ]
    defeated_indices = [
        i for i in range(attack_count) if i not in landed_indices
    ]

    lines: list[str] = []

    # Top of report
    lines.append("# rag-poison-lab")
    lines.append("")
    lines.append("Multi-model comparative report")
    lines.append("")
    lines.append(f"*Generated {timestamp}*")
    lines.append("")

    # Executive callout
    if total_landings > 0:
        lines.append(
            f"> **{total_landings} of {total_runs} attack-model combinations landed** "
            f"({lab_mode} lab configuration)."
        )
    else:
        lines.append(
            f"> **0 of {total_runs} attack-model combinations landed** "
            f"({lab_mode} lab configuration). All attacks defeated across all completed models."
        )
    if errored_rows:
        lines.append("")
        lines.append(
            f"> ⚠️ **{len(errored_rows)} of {model_count} models errored** during this run "
            "and produced no results. See the Errors section below."
        )
    lines.append("")

    # Metadata table
    lines.extend([
        "| Mode | Models | Attacks per model | Total runs | Landings |",
        "|:-:|:-:|:-:|:-:|:-:|",
        f"| `{lab_mode}` | {model_count} | {attack_count} | {total_runs} | **{total_landings}** |",
        "",
    ])

    # Brief methodology pointer; full explanation lives in the project README.
    lines.extend([
        "Canary tokens are test instruments (not real secrets); refusal-context "
        "mentions are filtered out; `attacker.example` is a reserved TLD that "
        "does not resolve. Full methodology: see the project README.",
        "",
    ])

    # Landing matrix
    lines.append("## Landing matrix")
    lines.append("")
    lines.append("Click any attack name to jump to its detail.")
    lines.append("")
    model_headers = " | ".join(f"**{row.spec.label}**" for row in rows)
    lines.append(f"| Attack | {model_headers} |")
    separator = " | ".join([":-:"] * model_count)
    lines.append(f"|:--| {separator} |")

    if ok_rows:
        for i in range(attack_count):
            attack = ok_rows[0].results[i].attack
            anchor_text = f"a{i + 1:02d} {attack.family} {attack.payload_id}"
            anchor_slug = _slug(anchor_text)
            attack_label = f"[`{attack.family}` / `{attack.payload_id}`](#{anchor_slug})"
            cells: list[str] = []
            for row in rows:
                if row.error:
                    cells.append("⚠️")
                elif i < len(row.results) and row.results[i].landed:
                    cells.append("✅")
                else:
                    cells.append("❌")
            cells_str = " | ".join(cells)
            lines.append(f"| {attack_label} | {cells_str} |")

    totals = []
    for row in rows:
        if row.error:
            totals.append("**errored**")
        else:
            landed = sum(1 for r in row.results if r.landed)
            totals.append(f"**{landed} / {attack_count}**")
    totals_str = " | ".join(totals)
    lines.append(f"| **Total** | {totals_str} |")
    lines.append("")

    # By-model quick summary
    lines.append("## By model")
    lines.append("")
    for row in rows:
        if row.error:
            lines.append(
                f"- **{row.spec.label}** (`{row.spec.model}`): "
                f"⚠️ errored, no results recorded"
            )
            continue
        landed_names = [
            f"`{r.attack.family}/{r.attack.payload_id}`" for r in row.results if r.landed
        ]
        landed_count = len(landed_names)
        if landed_count:
            landed_str = ", ".join(landed_names)
            lines.append(
                f"- **{row.spec.label}** (`{row.spec.model}`): "
                f"**{landed_count} of {attack_count} landed**: {landed_str}"
            )
        else:
            lines.append(
                f"- **{row.spec.label}** (`{row.spec.model}`): "
                f"0 of {attack_count} landed, all attacks defeated"
            )
    lines.append("")

    # Errors section (if any models failed)
    if errored_rows:
        lines.append("## Errors")
        lines.append("")
        for row in errored_rows:
            lines.append(
                f"- **{row.spec.label}** (`{row.spec.provider}` / `{row.spec.model}`): "
                f"`{row.error}`"
            )
        lines.append("")

    # Landings (the actual interesting findings)
    if landed_indices:
        lines.append("## Landings")
        lines.append("")
        lines.append(
            "Attacks that succeeded against at least one model. These are the "
            "findings worth writing up."
        )
        lines.append("")

        for i in landed_indices:
            attack = ok_rows[0].results[i].attack
            anchor_text = f"a{i + 1:02d} {attack.family} {attack.payload_id}"
            landed_on = [row.spec.label for row in ok_rows if _row_landed_at(row, i)]
            impact = _PRODUCTION_IMPACT.get(attack.family)

            lines.append(f"### {anchor_text}")
            lines.append("")
            lines.append(f"> **✅ LANDED** on: {', '.join(landed_on)}  ")
            lines.append(f"> Family: `{attack.family}` · Payload: `{attack.payload_id}` · Severity: `{attack.severity}`")
            lines.append("")
            lines.append(f"**Description:** {attack.description}")
            lines.append("")
            if impact:
                lines.append(f"**Production impact:** {impact}")
                lines.append("")
            lines.append("**Poisoned document:**")
            lines.append("")
            lines.append("```")
            lines.append(attack.build_document())
            lines.append("```")
            lines.append("")
            lines.append(f"**Probe question:** {attack.probe_question()}")
            lines.append("")

            for row in ok_rows:
                if i >= len(row.results):
                    continue
                r = row.results[i]
                mark = "✅ LANDED" if r.landed else "❌ defeated"
                lines.append(f"#### {row.spec.label}: {mark}")
                lines.append("")
                lines.append("```")
                lines.append(r.response)
                lines.append("```")
                lines.append("")

    # Defeated attacks (collapsed)
    if defeated_indices:
        lines.append("## Defeated attacks")
        lines.append("")
        lines.append("<details>")
        lines.append(
            f"<summary><strong>{len(defeated_indices)} attacks were defeated "
            "across all models</strong> (expand to inspect responses)</summary>"
        )
        lines.append("")

        for i in defeated_indices:
            attack = ok_rows[0].results[i].attack
            anchor_text = f"a{i + 1:02d} {attack.family} {attack.payload_id}"

            lines.append(f"### {anchor_text}")
            lines.append("")
            lines.append(f"> ❌ **Defeated** by all models")
            lines.append(f"> Family: `{attack.family}` · Payload: `{attack.payload_id}` · Severity if landed: `{attack.severity}`")
            lines.append("")
            lines.append(f"**Description:** {attack.description}")
            lines.append("")
            lines.append("**Poisoned document:**")
            lines.append("")
            lines.append("```")
            lines.append(attack.build_document())
            lines.append("```")
            lines.append("")
            lines.append(f"**Probe question:** {attack.probe_question()}")
            lines.append("")

            for row in ok_rows:
                if i >= len(row.results):
                    continue
                r = row.results[i]
                lines.append(f"#### {row.spec.label}: defeated")
                lines.append("")
                lines.append("```")
                lines.append(r.response[:1000])
                lines.append("```")
                lines.append("")

        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)
