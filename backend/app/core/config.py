"""Small dependency-free settings loader for local development."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
REPOSITORY_DIRECTORY = BACKEND_DIRECTORY.parent
ENV_FILE = REPOSITORY_DIRECTORY / ".env"
BACKEND_ENV_FILE = BACKEND_DIRECTORY / ".env"


def _file_settings() -> dict[str, str]:
    settings: dict[str, str] = {}
    # The repository .env is the documented default. A backend-specific .env can
    # override it for local development without ever overriding OS environment vars.
    for env_file in (ENV_FILE, BACKEND_ENV_FILE):
        if not env_file.exists():
            continue
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", maxsplit=1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            settings[key.strip()] = value
    return settings


def get_setting(name: str, default: str | None = None) -> str | None:
    """Read an environment variable, falling back to repo or backend .env files."""
    return os.environ.get(name) or _file_settings().get(name, default)


def get_openai_api_key() -> str:
    api_key = get_setting("OPENAI_API_KEY")
    if not api_key or api_key == "sk-...":
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return api_key


def get_openai_model() -> str:
    return get_setting("OPENAI_MODEL", "gpt-5.6") or "gpt-5.6"


def is_demo_mode() -> bool:
    """Enable deterministic sample-data flows only when explicitly requested."""
    return (get_setting("DEMO_MODE", "false") or "false").lower() in {"1", "true", "yes"}


def get_segmentation_as_of_date() -> date:
    """Return a configurable as-of date for fixtures, otherwise today's date."""
    configured = get_setting("SEGMENTATION_AS_OF_DATE")
    if not configured:
        return date.today()
    try:
        return date.fromisoformat(configured)
    except ValueError as exc:
        raise RuntimeError("SEGMENTATION_AS_OF_DATE must use YYYY-MM-DD.") from exc


def allow_unsafe_local_sandbox() -> bool:
    """Never enable live generated-code execution locally by default."""
    return (get_setting("ALLOW_UNSAFE_LOCAL_SANDBOX", "false") or "false").lower() in {"1", "true", "yes"}


def get_database_path() -> Path:
    configured_path = Path(get_setting("DATABASE_PATH", "./winback.sqlite3") or "./winback.sqlite3")
    return configured_path if configured_path.is_absolute() else BACKEND_DIRECTORY / configured_path
