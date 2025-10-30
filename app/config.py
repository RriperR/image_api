from __future__ import annotations

from typing import Union, List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PositiveInt, field_validator


class Settings(BaseSettings):
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: PositiveInt = Field(default=8080)

    CLIENT_MAX_SIZE_MB: PositiveInt = Field(default=20)
    MAX_IMAGE_MB: PositiveInt = Field(default=20)
    MAX_PIXELS: PositiveInt = Field(default=50_000_000)
    DEFAULT_QUALITY: int = Field(default=85, ge=1, le=95)

    DATABASE_URL: str

    # --- auth ---
    API_TOKENS: Union[str, List[str]] = Field(default="")

    # --- logging ---
    LOG_PATH: str = Field(default="./logs/app.log")
    LOG_MAX_BYTES: PositiveInt = Field(default=1_048_576)
    LOG_BACKUPS: PositiveInt = Field(default=5)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("API_TOKENS", mode="before")
    @classmethod
    def split_tokens(cls, v):
        if not v:
            return []
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v if str(x).strip()]
        # comma-separated
        return [token.strip() for token in str(v).split(",") if token.strip()]


def get_settings() -> Settings:
    return Settings()
