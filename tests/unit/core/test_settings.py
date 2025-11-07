from __future__ import annotations

from pathlib import Path

import pytest

from chatbot.core.config import AppSettings, PostgresSettings

pytestmark = pytest.mark.unit


def test_postgres_settings_env_precedence(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "POSTGRES_HOST=from_env_file",
                "POSTGRES_DB=brand_store",
                "POSTGRES_USER=file_user",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("POSTGRES_HOST", "from_environment")
    settings = PostgresSettings(_env_file=env_file)

    assert settings.host == "from_environment"
    assert settings.database == "brand_store"
    assert settings.user == "file_user"


def test_app_settings_composes_sub_settings(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://example:6379/1")
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")

    settings = AppSettings()

    assert settings.redis.url == "redis://example:6379/1"
    assert settings.llm.provider.value == "openrouter"
