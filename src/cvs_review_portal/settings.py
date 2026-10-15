"""Validated application configuration for the CVS Review Portal."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnvironment = Literal["local", "dev", "staging", "prod"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
StorageBackend = Literal["local", "azure_blob"]
IdentityMode = Literal["disabled", "development", "azure_app_service"]
DatasetLayout = Literal["legacy", "video_catalog"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and an optional `.env` file.

    Invalid values raise `pydantic.ValidationError` at construction; there is no
    silent fallback. Missing Azure configuration does not fall back to local data.
    Development identity is never enabled automatically merely because production
    identity is absent.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnvironment = "local"
    app_version: str = Field(default="0.1.0", min_length=1)
    log_level: LogLevel = "INFO"
    data_root: Path = Field(default=Path("demo-data"))

    storage_backend: StorageBackend = "local"
    azure_storage_account_url: str | None = None
    azure_blob_container: str | None = None

    # legacy: load monolithic dataset.json. video_catalog: videos.csv + per-video JSON
    # (dataset.json is not read at runtime). Default preserves demo fixtures and tests.
    dataset_layout: DatasetLayout = "legacy"

    identity_mode: IdentityMode = "disabled"
    development_actor: str | None = None
    allowed_actors: str = ""

    @field_validator("app_env", mode="before")
    @classmethod
    def _normalize_app_env(cls, value: object) -> object:
        if isinstance(value, str):
            return value.lower()
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("storage_backend", "identity_mode", "dataset_layout", mode="before")
    @classmethod
    def _normalize_lower(cls, value: object) -> object:
        if isinstance(value, str):
            return value.lower().strip()
        return value

    @model_validator(mode="after")
    def _validate_storage_and_identity(self) -> Settings:
        if self.storage_backend == "azure_blob":
            if not self.azure_storage_account_url or not self.azure_storage_account_url.strip():
                raise ValueError(
                    "AZURE_STORAGE_ACCOUNT_URL is required when STORAGE_BACKEND=azure_blob"
                )
            if not self.azure_blob_container or not self.azure_blob_container.strip():
                raise ValueError("AZURE_BLOB_CONTAINER is required when STORAGE_BACKEND=azure_blob")

        if self.identity_mode == "development":
            if not self.development_actor or not self.development_actor.strip():
                raise ValueError("DEVELOPMENT_ACTOR is required when IDENTITY_MODE=development")
            if self.app_env not in ("local", "dev"):
                raise ValueError(
                    "IDENTITY_MODE=development is only allowed for APP_ENV=local or dev"
                )

        if self.identity_mode == "azure_app_service":
            if not self.allowed_actor_set():
                raise ValueError("ALLOWED_ACTORS is required when IDENTITY_MODE=azure_app_service")

        return self

    def allowed_actor_set(self) -> frozenset[str]:
        parts = [part.strip() for part in self.allowed_actors.split(",")]
        return frozenset(part for part in parts if part)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached default settings instance.

    Used only when `create_app()` receives no injected settings.
    """
    return Settings()
