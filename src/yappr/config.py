from __future__ import annotations

import os
import tomllib
from pathlib import Path

import typer
from dotenv import load_dotenv
from platformdirs import user_config_dir
from pydantic import BaseModel, ConfigDict

DEFAULT_BASE_URL = "https://api.peec.ai/customer/v1"
CONFIG_DIR = Path(user_config_dir("yappr"))
CONFIG_PATH = CONFIG_DIR / "config.toml"


class ConfigError(RuntimeError):
    """Raised when local yappr configuration is missing or invalid."""


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str
    default_project_id: str | None = None
    base_url: str = DEFAULT_BASE_URL


class UserConfig(BaseModel):
    api_key: str | None = None
    default_project_id: str | None = None
    base_url: str | None = None


def ensure_settings(*, interactive: bool) -> Settings:
    settings = load_settings()
    if settings is not None:
        return settings

    if not interactive:
        raise ConfigError(_missing_key_message())

    typer.echo("yappr needs a Peec API key.\n")
    typer.echo("Get one at: https://peec.ai/mcp-challenge (30 days free during the challenge)\n")
    api_key = typer.prompt("Paste your key", hide_input=True).strip()
    if not api_key:
        raise ConfigError("A Peec API key is required to continue.")

    save_user_config(api_key=api_key)
    typer.secho(f"Saved to {CONFIG_PATH}", fg="green")
    refreshed = load_settings()
    if refreshed is None:
        raise ConfigError("The API key was saved, but yappr could not reload its configuration.")
    return refreshed


def load_settings() -> Settings | None:
    load_dotenv(override=False)
    user_config = load_user_config()

    api_key = os.getenv("PEEC_API_KEY") or user_config.api_key
    if not api_key:
        return None

    default_project_id = os.getenv("PEEC_PROJECT_ID") or user_config.default_project_id
    base_url = os.getenv("PEEC_BASE_URL") or user_config.base_url or DEFAULT_BASE_URL
    return Settings(api_key=api_key, default_project_id=default_project_id, base_url=base_url)


def load_user_config() -> UserConfig:
    if not CONFIG_PATH.exists():
        return UserConfig()

    try:
        payload = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Failed to read {CONFIG_PATH}: {exc}") from exc

    return UserConfig.model_validate(payload)


def save_user_config(
    *,
    api_key: str | None = None,
    default_project_id: str | None = None,
    base_url: str | None = None,
) -> None:
    current = load_user_config()
    merged = UserConfig(
        api_key=api_key or current.api_key,
        default_project_id=default_project_id or current.default_project_id,
        base_url=base_url or current.base_url,
    )

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    if merged.api_key:
        lines.append(f'api_key = "{_escape_toml_string(merged.api_key)}"')
    if merged.default_project_id:
        lines.append(f'default_project_id = "{_escape_toml_string(merged.default_project_id)}"')
    if merged.base_url:
        lines.append(f'base_url = "{_escape_toml_string(merged.base_url)}"')

    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _missing_key_message() -> str:
    return (
        "yappr needs a Peec API key. Set PEEC_API_KEY, add it to a local .env file, "
        f"or save it in {CONFIG_PATH}."
    )
