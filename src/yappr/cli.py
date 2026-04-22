from __future__ import annotations

import json
from typing import Annotated

import typer

from yappr.config import ConfigError, ensure_settings
from yappr.peec.client import PeecAPIError, PeecClient, PeecClientError
from yappr.peec.models import Project

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
            projects = client.list_projects()
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output)
    except (PeecClientError, PeecAPIError) as exc:
        _exit_with_error(str(exc), json_output)

    if not projects:
        _exit_with_error("No Peec projects are available for this API key.", json_output)

    try:
        selected_project = _select_project(projects, project_id or settings.default_project_id)
    except ConfigError as exc:
        _exit_with_error(str(exc), json_output)

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "domain": domain,
                    "project": selected_project.model_dump(),
                }
            )
        )
        return

    typer.echo(f"Auditing {domain}")
    typer.echo(f"Project: {selected_project.name}")


def _exit_with_error(message: str, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps({"error": message}))
    else:
        typer.secho(message, fg="red", err=True)
    raise typer.Exit(code=1)
