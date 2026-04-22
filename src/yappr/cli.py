from __future__ import annotations

import json
import webbrowser
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer
from rich.box import SIMPLE
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from yappr.audit import build_report
from yappr.config import ConfigError, ensure_settings
from yappr.peec.client import PeecAPIError, PeecClient, PeecClientError
from yappr.peec.models import (
    AIModel,
    Brand,
    DomainSource,
    Opportunity,
    PeecData,
    Project,
    Topic,
    URLSource,
)
from yappr.render.html import render_report as render_html_report
from yappr.render.terminal import render_report as render_terminal_report

app = typer.Typer(
    add_completion=False,
    help="Audit your website's AI search visibility with Peec.",
    no_args_is_help=True,
)

console = Console()


@dataclass(frozen=True)
class ProjectContext:
    project: Project | None
    scope: str
    brands: list[Brand]
    brand: Brand


@dataclass(frozen=True)
class Window:
    start: str
    end: str


@app.callback()
def main() -> None:
    """yappr CLI."""


def _select_project(projects: list[Project], requested_project_id: str | None) -> Project:
    if requested_project_id is None:
        return projects[0]

    for project in projects:
        if project.id == requested_project_id:
            return project

    raise ConfigError(
        f"Project '{requested_project_id}' was not found in your Peec account. "
        "Pass a valid --project-id or update PEEC_PROJECT_ID."
    )


def _normalize_domain(domain: str) -> str:
    parsed = urlparse(domain if "://" in domain else f"https://{domain}")
    host = parsed.netloc or parsed.path
    return host.lower().strip("/")


def _match_brand(brands: list[Brand], domain: str) -> Brand:
    normalized = _normalize_domain(domain)
    for brand in brands:
        for tracked_domain in brand.domains:
            if _normalize_domain(tracked_domain) == normalized:
                return brand

    raise ConfigError(
        f"{domain} isn't tracked in this Peec project. "
        "Use a tracked domain or add it in Peec first."
    )


@app.command()
def audit(
    domain: str,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    days: Annotated[int, typer.Option("--days", min=1)] = 30,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON only.")] = False,
    html: Annotated[bool, typer.Option("--html", help="Generate an HTML report.")] = False,
) -> None:
    """Run an AI visibility audit for a tracked domain."""
    if json_output and html:
        _exit_with_error("Use either --json or --html, not both together.", json_output=True)

    window = _window(days)

    try:
        settings = ensure_settings(interactive=not json_output)
        with PeecClient(api_key=settings.api_key, base_url=settings.base_url) as client:
            if json_output:
                audit_report = _run_audit(
                    client=client,
                    domain=domain,
                    requested_project_id=project_id or settings.default_project_id,
                    start_date=window.start,
                    end_date=window.end,
                )
            else:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True,
                ) as progress:
                    task_id = progress.add_task("Connecting to Peec…", total=None)
                    audit_report = _run_audit(
                        client=client,
                        domain=domain,
                        requested_project_id=project_id or settings.default_project_id,
                        start_date=window.start,
                        end_date=window.end,
                        progress=progress,
                        task_id=task_id,
                    )
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output)
    except (PeecClientError, PeecAPIError) as exc:
        _exit_with_error(str(exc), json_output)

    html_path: Path | None = None
    if html:
        html_path = Path.cwd() / "yappr-report.html"
        html_path.write_text(render_html_report(audit_report), encoding="utf-8")
        with suppress(Exception):
            webbrowser.open(html_path.as_uri())

    if json_output:
        typer.echo(audit_report.model_dump_json())
    else:
        render_terminal_report(
            console,
            audit_report,
            html_path=str(html_path) if html_path is not None else None,
        )

    raise typer.Exit(code=_exit_code_for_score(audit_report.score))


@app.command("peek")
def peek(
    domain: str,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    days: Annotated[int, typer.Option("--days", min=1)] = 30,
    topic: Annotated[str | None, typer.Option("--topic")] = None,
    model: Annotated[str | None, typer.Option("--model")] = None,
    gap: Annotated[bool, typer.Option("--gap")] = False,
    limit: Annotated[int, typer.Option("--limit", min=1, max=15)] = 5,
) -> None:
    """Peek into the evidence behind the score."""
    window = _window(days)
    try:
        settings = ensure_settings(interactive=True)
        with PeecClient(api_key=settings.api_key, base_url=settings.base_url) as client:
            context = _load_context(client, domain, project_id or settings.default_project_id)
            topic_match = _resolve_topic(client, context, topic) if topic else None
            model_match = _resolve_model(client, context, model) if model else None
            filters = _segment_filters(topic_match, model_match)
            brand_rows = client.get_brand_report(
                project_id=_project_id(context),
                start_date=window.start,
                end_date=window.end,
                filters=filters or None,
            )
            source_filters = list(filters)
            if gap:
                source_filters.append({"field": "gap", "operator": "gte", "value": 1})
            else:
                source_filters.append(
                    {
                        "field": "mentioned_brand_id",
                        "operator": "in",
                        "values": [context.brand.id],
                    }
                )
            domain_rows = client.get_domain_report(
                project_id=_project_id(context),
                start_date=window.start,
                end_date=window.end,
                filters=source_filters,
                limit=max(limit * 3, 20),
            )
            url_rows = client.get_url_report(
                project_id=_project_id(context),
                start_date=window.start,
                end_date=window.end,
                filters=source_filters,
                limit=max(limit * 3, 20),
            )
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output=False)
    except (PeecClientError, PeecAPIError) as exc:
        _exit_with_error(str(exc), json_output=False)

    own_row = _brand_row(brand_rows, context.brand.id)
    competitors = [row for row in brand_rows if _brand_id(row) != context.brand.id]
    top_competitor = max(competitors, key=lambda row: _float(row, "visibility"), default=None)

    _print_title("peek", domain, window, context, topic_match, model_match, gap)
    stats = Table(box=SIMPLE)
    stats.add_column("Metric")
    stats.add_column("Value", justify="right")
    stats.add_row("Visibility", f"{round(_float(own_row, 'visibility') * 100)}%")
    stats.add_row("Mentions", str(_int(own_row, "mention_count")))
    stats.add_row("Sentiment", str(round(_float(own_row, "sentiment"))))
    stats.add_row("Total chats", str(_int(own_row, "visibility_total")))
    if top_competitor is not None:
        stats.add_row(
            "Top competitor",
            f"{_brand_name(top_competitor)} ({round(_float(top_competitor, 'visibility') * 100)}%)",
        )
    console.print(stats)
    console.print()
    console.print(_domain_table(domain_rows[:limit], title="Top Domains"))
    console.print()
    console.print(_url_table(url_rows[:limit], title="Top URLs"))


@app.command("cite")
def cite(
    domain: str,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    days: Annotated[int, typer.Option("--days", min=1)] = 30,
    gap: Annotated[bool, typer.Option("--gap")] = False,
    limit: Annotated[int, typer.Option("--limit", min=1, max=20)] = 10,
) -> None:
    """Show the domains and URLs shaping visibility."""
    window = _window(days)
    try:
        settings = ensure_settings(interactive=True)
        with PeecClient(api_key=settings.api_key, base_url=settings.base_url) as client:
            context = _load_context(client, domain, project_id or settings.default_project_id)
            filters = []
            if gap:
                filters.append({"field": "gap", "operator": "gte", "value": 1})
            else:
                filters.append(
                    {
                        "field": "mentioned_brand_id",
                        "operator": "in",
                        "values": [context.brand.id],
                    }
                )
            domain_rows = client.get_domain_report(
                project_id=_project_id(context),
                start_date=window.start,
                end_date=window.end,
                filters=filters,
                limit=max(limit * 3, 30),
            )
            url_rows = client.get_url_report(
                project_id=_project_id(context),
                start_date=window.start,
                end_date=window.end,
                filters=filters,
                limit=max(limit * 3, 30),
            )
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output=False)
    except (PeecClientError, PeecAPIError) as exc:
        _exit_with_error(str(exc), json_output=False)

    _print_title("cite", domain, window, context, gap=gap)
    console.print(_domain_table(domain_rows[:limit], title="Domains"))
    console.print()
    console.print(_url_table(url_rows[:limit], title="URLs"))


@app.command("diff")
def diff_(
    domain: str,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    days: Annotated[int, typer.Option("--days", min=1)] = 30,
) -> None:
    """Compare this window against the previous one."""
    current = _window(days)
    previous = _previous_window(current, days)
    try:
        settings = ensure_settings(interactive=True)
        with PeecClient(api_key=settings.api_key, base_url=settings.base_url) as client:
            current_report = _run_audit(
                client=client,
                domain=domain,
                requested_project_id=project_id or settings.default_project_id,
                start_date=current.start,
                end_date=current.end,
            )
            previous_report = _run_audit(
                client=client,
                domain=domain,
                requested_project_id=project_id or settings.default_project_id,
                start_date=previous.start,
                end_date=previous.end,
            )
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output=False)
    except (PeecClientError, PeecAPIError) as exc:
        _exit_with_error(str(exc), json_output=False)

    console.print(
        f"[bold]yappr[/bold] · diff · {domain}\n"
        f"[dim]{current.start} → {current.end} vs {previous.start} → {previous.end}[/dim]\n"
    )
    delta = current_report.score - previous_report.score
    summary = Table(box=SIMPLE)
    summary.add_column("Window")
    summary.add_column("Score", justify="right")
    summary.add_row("Current", str(current_report.score))
    summary.add_row("Previous", str(previous_report.score))
    summary.add_row("Delta", _signed(delta))
    console.print(summary)
    console.print()

    check_table = Table(title="Check Delta", box=SIMPLE)
    check_table.add_column("Check")
    check_table.add_column("Current", justify="right")
    check_table.add_column("Previous", justify="right")
    check_table.add_column("Delta", justify="right")
    previous_checks = {check.id: check for check in previous_report.checks}
    for check in current_report.checks:
        earlier = previous_checks[check.id]
        check_table.add_row(
            check.name,
            str(check.score),
            str(earlier.score),
            _signed(check.score - earlier.score),
        )
    console.print(check_table)
    raise typer.Exit(code=_exit_code_for_score(current_report.score))


@app.command("next")
def next_(
    domain: str,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    days: Annotated[int, typer.Option("--days", min=1)] = 30,
) -> None:
    """Show the next best moves with evidence."""
    window = _window(days)
    try:
        settings = ensure_settings(interactive=True)
        with PeecClient(api_key=settings.api_key, base_url=settings.base_url) as client:
            context = _load_context(client, domain, project_id or settings.default_project_id)
            data = client.fetch_audit_data(
                project_id=_project_id(context),
                project_name=context.project.name if context.project else None,
                project_scope=context.scope,
                target_domain=_normalize_domain(domain),
                own_brand=context.brand,
                brands=context.brands,
                start_date=window.start,
                end_date=window.end,
            )
            report = build_report(data)
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output=False)
    except (PeecClientError, PeecAPIError) as exc:
        _exit_with_error(str(exc), json_output=False)

    _print_title("next", domain, window, context)
    for opportunity in report.opportunities:
        console.print(
            f"[bold]{opportunity.id}. [{opportunity.category}][/bold] "
            f"{opportunity.label} [green]+{opportunity.impact} pts[/green]"
        )
        for evidence in _opportunity_evidence(opportunity, data)[:3]:
            console.print(f"  • {evidence}", style="dim")
        console.print()


def _run_audit(
    *,
    client: PeecClient,
    domain: str,
    requested_project_id: str | None,
    start_date: str,
    end_date: str,
    progress: Progress | None = None,
    task_id: TaskID | None = None,
):
    context = _load_context(client, domain, requested_project_id)
    if progress is not None and task_id is not None:
        progress.update(task_id, description="Fetching Peec reports…")
    data = client.fetch_audit_data(
        project_id=_project_id(context),
        project_name=context.project.name if context.project else None,
        project_scope=context.scope,
        target_domain=_normalize_domain(domain),
        own_brand=context.brand,
        brands=context.brands,
        start_date=start_date,
        end_date=end_date,
    )
    if progress is not None and task_id is not None:
        progress.update(task_id, description="Scoring audit…")
    return build_report(data)


def _load_context(
    client: PeecClient,
    domain: str,
    requested_project_id: str | None,
) -> ProjectContext:
    project, brands, scope = _resolve_scope(
        client=client,
        requested_project_id=requested_project_id,
    )
    brand = _match_brand(brands, domain)
    return ProjectContext(project=project, scope=scope, brands=brands, brand=brand)


def _resolve_scope(
    *,
    client: PeecClient,
    requested_project_id: str | None,
) -> tuple[Project | None, list[Brand], str]:
    try:
        projects = client.list_projects()
    except PeecAPIError as exc:
        if "Not a Company API Key" not in str(exc):
            raise
        projects = []

    if projects:
        selected_project = _select_project(projects, requested_project_id)
        return selected_project, client.list_brands(project_id=selected_project.id), "company"

    return None, client.list_brands(), "project"


def _resolve_topic(
    client: PeecClient,
    context: ProjectContext,
    query: str,
) -> Topic:
    topics = client.list_topics(project_id=_project_id(context))
    return _match_named(topics, query, "topic")


def _resolve_model(
    client: PeecClient,
    context: ProjectContext,
    query: str,
) -> AIModel:
    models = client.list_models(project_id=_project_id(context))
    return _match_named(models, query, "model")


def _match_named(items: list[Topic] | list[AIModel], query: str, label: str):
    lowered = query.lower()
    exact = [item for item in items if item.name.lower() == lowered]
    if exact:
        return exact[0]
    partial = [item for item in items if lowered in item.name.lower()]
    if len(partial) == 1:
        return partial[0]
    if partial:
        names = ", ".join(item.name for item in partial[:5])
        raise ConfigError(f"Ambiguous {label} '{query}'. Matches: {names}.")
    raise ConfigError(f"No {label} matched '{query}'.")


def _segment_filters(topic: Topic | None, model: AIModel | None) -> list[dict[str, object]]:
    filters: list[dict[str, object]] = []
    if topic is not None:
        filters.append({"field": "topic_id", "operator": "in", "values": [topic.id]})
    if model is not None:
        filters.append({"field": "model_id", "operator": "in", "values": [model.id]})
    return filters


def _window(days: int) -> Window:
    end = date.today()
    start = end - timedelta(days=days)
    return Window(start=start.isoformat(), end=end.isoformat())


def _previous_window(current: Window, days: int) -> Window:
    current_start = date.fromisoformat(current.start)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days)
    return Window(start=previous_start.isoformat(), end=previous_end.isoformat())


def _print_title(
    command: str,
    domain: str,
    window: Window,
    context: ProjectContext,
    topic: Topic | None = None,
    model: AIModel | None = None,
    gap: bool = False,
) -> None:
    console.print(f"[bold]yappr[/bold] · {command} · {domain}")
    console.print(f"[dim]Window: {window.start} → {window.end}[/dim]")
    console.print(f"[dim]Brand: {context.brand.name}[/dim]")
    if topic is not None:
        console.print(f"[dim]Topic: {topic.name}[/dim]")
    if model is not None:
        console.print(f"[dim]Model: {model.name}[/dim]")
    if gap:
        console.print("[dim]Mode: gap only[/dim]")
    console.print()


def _domain_table(rows: list[DomainSource], title: str) -> Table:
    table = Table(title=title, box=SIMPLE)
    table.add_column("Domain")
    table.add_column("Type")
    table.add_column("Retrieved", justify="right")
    table.add_column("Citation", justify="right")
    for row in rows:
        table.add_row(
            row.domain,
            row.classification or "n/a",
            f"{round(row.retrieved_percentage * 100)}%",
            f"{row.citation_rate:.2f}",
        )
    return table


def _url_table(rows: list[URLSource], title: str) -> Table:
    table = Table(title=title, box=SIMPLE)
    table.add_column("Page")
    table.add_column("Type")
    table.add_column("Retrievals", justify="right")
    table.add_column("Citations", justify="right")
    for row in rows:
        label = row.title or row.url
        if len(label) > 70:
            label = f"{label[:67]}..."
        table.add_row(
            label,
            row.classification or "n/a",
            str(row.retrievals),
            str(row.citation_count),
        )
    return table


def _opportunity_evidence(opportunity: Opportunity, data: PeecData) -> list[str]:
    if opportunity.category == "EDITORIAL":
        examples = []
        for row in data.gap_url_sources:
            if row.classification:
                label = row.title or row.url
                examples.append(f"{row.classification.title()}: {label}")
        return examples
    if opportunity.category in {"UGC", "REFERENCE"}:
        target = opportunity.label.removeprefix("Build presence on ").strip().lower()
        matches = [
            f"{row.domain} ({row.classification or 'n/a'})"
            for row in data.gap_sources
            if row.domain.lower() == target
        ]
        return matches or [
            f"{row.domain} ({row.classification or 'n/a'})"
            for row in data.gap_sources
            if row.classification == opportunity.category
        ]
    if opportunity.category == "OWNED":
        return [
            f"Weak topic: {topic.topic_name}"
            for topic in sorted(
                data.topics,
                key=lambda item: item.competitor_max_visibility - item.visibility,
                reverse=True,
            )
            if topic.competitor_max_visibility > topic.visibility
        ]
    return []


def _brand_row(rows: list[dict[str, object]], brand_id: str) -> dict[str, object]:
    for row in rows:
        if _brand_id(row) == brand_id:
            return row
    return {}


def _brand_id(row: dict[str, object]) -> str | None:
    brand = row.get("brand")
    if isinstance(brand, dict):
        brand_id = brand.get("id")
        if isinstance(brand_id, str):
            return brand_id
    brand_id = row.get("brand_id")
    return brand_id if isinstance(brand_id, str) else None


def _brand_name(row: dict[str, object]) -> str:
    brand = row.get("brand")
    if isinstance(brand, dict):
        name = brand.get("name")
        if isinstance(name, str):
            return name
    name = row.get("brand_name")
    return name if isinstance(name, str) else "n/a"


def _float(row: dict[str, object], key: str) -> float:
    value = row.get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _int(row: dict[str, object], key: str) -> int:
    value = row.get(key)
    return int(value) if isinstance(value, (int, float)) else 0


def _signed(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def _project_id(context: ProjectContext) -> str | None:
    return context.project.id if context.project is not None else None


def _exit_code_for_score(score: int) -> int:
    if score >= 70:
        return 0
    if score >= 40:
        return 1
    return 2


def _exit_with_error(message: str, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps({"error": message}))
    else:
        typer.secho(message, fg="red", err=True)
    raise typer.Exit(code=1)


TaskID = int
