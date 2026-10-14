"""Tests for settings validation, environment loading, and cache behaviour."""

from collections.abc import Iterator

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from cvs_review_portal.settings import AppEnvironment, LogLevel, Settings, get_settings


class IsolatedSettings(Settings):
    """Settings that never load the developer's real `.env` file."""

    model_config = SettingsConfigDict(env_file=None)


@pytest.fixture()
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "APP_ENV",
        "APP_VERSION",
        "LOG_LEVEL",
        "DATA_ROOT",
        "STORAGE_BACKEND",
        "AZURE_STORAGE_ACCOUNT_URL",
        "AZURE_BLOB_CONTAINER",
        "IDENTITY_MODE",
        "DEVELOPMENT_ACTOR",
        "ALLOWED_ACTORS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults(clean_environment: None) -> None:
    settings = IsolatedSettings()
    assert settings.app_env == "local"
    assert settings.app_version == "0.1.0"
    assert settings.log_level == "INFO"
    assert settings.data_root.name == "demo-data"


@pytest.mark.parametrize("env", ["local", "dev", "staging", "prod"])
def test_all_valid_app_env_values_accepted(env: AppEnvironment) -> None:
    settings = IsolatedSettings(app_env=env)
    assert settings.app_env == env


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_all_valid_log_levels_accepted(level: LogLevel) -> None:
    settings = IsolatedSettings(log_level=level)
    assert settings.log_level == level


def test_app_env_is_lowercased(clean_environment: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "STAGING")
    settings = IsolatedSettings()
    assert settings.app_env == "staging"


def test_log_level_is_uppercased(clean_environment: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "warning")
    settings = IsolatedSettings()
    assert settings.log_level == "WARNING"


def test_invalid_app_env_raises(clean_environment: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "invalid")
    with pytest.raises(ValidationError):
        IsolatedSettings()


def test_invalid_log_level_raises(clean_environment: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")
    with pytest.raises(ValidationError):
        IsolatedSettings()


def test_empty_app_version_raises() -> None:
    with pytest.raises(ValidationError):
        IsolatedSettings(app_version="")


def test_environment_variable_loading(
    clean_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("APP_VERSION", "3.2.1")
    monkeypatch.setenv("LOG_LEVEL", "error")
    settings = IsolatedSettings()
    assert settings.app_env == "staging"
    assert settings.app_version == "3.2.1"
    assert settings.log_level == "ERROR"


def test_get_settings_returns_cached_instance(
    clear_settings_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("IDENTITY_MODE", "disabled")
    monkeypatch.delenv("DEVELOPMENT_ACTOR", raising=False)
    first = get_settings()
    second = get_settings()
    assert first is second
    assert first.app_env == "dev"


def test_cache_clear_picks_up_new_environment(
    clear_settings_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("IDENTITY_MODE", "disabled")
    monkeypatch.delenv("DEVELOPMENT_ACTOR", raising=False)
    assert get_settings().app_env == "dev"

    monkeypatch.setenv("APP_ENV", "prod")
    get_settings.cache_clear()
    assert get_settings().app_env == "prod"
