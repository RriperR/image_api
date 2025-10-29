from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PositiveInt


class Settings(BaseSettings):
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: PositiveInt = Field(default=8080)

    CLIENT_MAX_SIZE_MB: PositiveInt = Field(default=20)
    MAX_IMAGE_MB: PositiveInt = Field(default=20)
    MAX_PIXELS: PositiveInt = Field(default=50_000_000)

    DEFAULT_QUALITY: int = Field(default=85, ge=1, le=95)

    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
