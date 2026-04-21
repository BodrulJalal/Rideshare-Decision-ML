from __future__ import annotations

from dataclasses import dataclass, field
import os


def _split_origins(raw_origins: str) -> tuple[str, ...]:
    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
    return origins or ("*",)


@dataclass(frozen=True)
class Settings:
    api_title: str = "Driver Earnings Navigator API"
    api_description: str = (
        "FastAPI backend for rideshare driver zone recommendations and trip offer scoring."
    )
    api_version: str = "1.0.0"
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: _split_origins(os.getenv("BACKEND_CORS_ORIGINS", "*"))
    )


settings = Settings()
