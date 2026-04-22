from __future__ import annotations

import json
from typing import Annotated

import typer

from yappr.config import ConfigError, ensure_settings
from yappr.peec.client import PeecAPIError, PeecClient, PeecClientError
from yappr.peec.models import Brand, Project

app = typer.Typer(
    add_completion=False,
    help="Audit your website's AI search visibility with Peec.",
    no_args_is_help=True,
)


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


def _match_brand(brands: list[Brand], domain: str) -> Brand:
    normalized = domain.lower().removeprefix("https://").removeprefix("http://").strip("/")
    for brand in brands:
        for tracked_domain in brand.domains:
            if tracked_domain.lower().strip("/") == normalized:
                return brand

    raise ConfigError(
        f"{domain} isn't tracked in this Peec project. "
        "Use a tracked domain or add it in Peec first."
    )


@app.command()
def audit(
    domain: str,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON only.")] = False,
) -> None:
    """Run the initial Peec connectivity check for a tracked domain."""
    try:
        settings = ensure_settings(interactive=not json_output)
        with PeecClient(api_key=settings.api_key, base_url=settings.base_url) as client:
            try:
                projects = client.list_projects()
            except PeecAPIError as exc:
                if "Not a Company API Key" not in str(exc):
                    raise
                projects = []

            if projects:
                requested_project_id = project_id or settings.default_project_id
                selected_project = _select_project(projects, requested_project_id)
                brands = client.list_brands(project_id=selected_project.id)
                scope = "company"
            else:
                selected_project = None
                brands = client.list_brands()
                scope = "project"
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output)
    except (PeecClientError, PeecAPIError) as exc:
        _exit_with_error(str(exc), json_output)

    try:
        matched_brand = _match_brand(brands, domain)
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output)

    if json_output:
        payload = {
            "domain": domain,
            "scope": scope,
            "brand": matched_brand.model_dump(),
        }
        if selected_project is not None:
            payload["project"] = selected_project.model_dump()
        typer.echo(
            json.dumps(payload)
        )
        return

    typer.echo(f"Auditing {domain}")
    typer.echo(f"Brand: {matched_brand.name}")
    if selected_project is not None:
        typer.echo(f"Project: {selected_project.name}")
    else:
        typer.echo("Project scope: project-scoped API key")


def _exit_with_error(message: str, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps({"error": message}))
    else:
        typer.secho(message, fg="red", err=True)
    raise typer.Exit(code=1)
