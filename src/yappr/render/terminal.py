from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from yappr.peec.models import AuditReport
from yappr.scoring import status


def render_report(console: Console, report: AuditReport, *, html_path: str | None = None) -> None:
    rule = Text("─" * min(console.width - 1, 55), style="dim")
    console.print(rule)
    console.print(f"  [bold]yappr[/bold] · AI Visibility Audit · {report.domain}")
    console.print(rule)
    console.print(f"  Window:   {report.date_range[0]} → {report.date_range[1]}", style="dim")
    if report.models:
        console.print(f"  Models:   {', '.join(report.models)}", style="dim")
    console.print()
    console.print()
    console.print(Align.center(_score_panel(report)))
    console.print()

    for check in report.checks:
        symbol, color, _ = status(check.score)
        headline = Text()
        headline.append(f"  {symbol} ", style=color)
        headline.append(f"{check.name:<22}", style="bold")
        headline.append(f"{check.score:>3} / 100", style=color)
        console.print(headline)
        console.print(f"     {check.summary}", style="default")
        console.print()

    console.print(rule)
    console.print("  [bold]Top Opportunities[/bold] (ranked by impact)")
    console.print(rule)
    console.print()

    for opportunity in report.opportunities:
        line = Text()
        line.append(f"  {opportunity.id}. ", style="bold")
        line.append(f"[{opportunity.category}] ".ljust(13), style="cyan")
        line.append(f"{opportunity.label:<40}")
        line.append(f"+{opportunity.impact} pts", style="green")
        console.print(line)

    console.print()
    console.print("  → Run `yappr fix 1` to generate an action package. (coming soon)", style="dim")
    if html_path:
        console.print(f"  → Full report: {html_path}", style="dim")
    console.print(rule)


def _score_panel(report: AuditReport) -> Panel:
    score_text = _gradient_score(report.score, report.color)
    score_group = Group(
        Text(""),
        Align.center(score_text),
        Align.center(Text("/ 100", style="bold")),
        Text(""),
    )
    summary = Text()
    summary.append(f"{report.symbol} ", style=report.color)
    summary.append(report.label, style="bold")
    grid = Table.grid(padding=(0, 3))
    grid.add_row(
        Panel(score_group, box=box.ROUNDED, border_style=report.color, padding=(0, 4)),
        summary,
    )
    return Panel.fit(grid, box=box.SIMPLE, border_style="default", padding=(0, 1))


def _gradient_score(score: int, color: str) -> Text:
    palette = {
        "red": ["red3", "red", "bright_red"],
        "yellow": ["orange3", "yellow3", "yellow1"],
        "green": ["green3", "green", "spring_green2"],
    }
    shades = palette.get(color, [color])
    text = Text()
    digits = str(score)
    for index, character in enumerate(digits):
        text.append(character, style=f"bold {shades[index % len(shades)]}")
    return text
