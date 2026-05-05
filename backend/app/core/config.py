from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


DEFAULT_GEMINI_MODEL: Final[str] = "gemini-2.5-flash"
BACKEND_ROOT: Final[Path] = Path(__file__).resolve().parents[2]


load_dotenv(BACKEND_ROOT / ".env")


def _split_origins(raw_origins: str) -> tuple[str, ...]:
    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
    return origins or ("*",)


@dataclass(frozen=True)
class Settings:
    api_title: str = "Driver Earnings Navigator API"
    api_description: str = (
        "FastAPI backend for rideshare driver relocation recommendations and copilot chat."
    )
    api_version: str = "1.0.0"
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: _split_origins(os.getenv("BACKEND_CORS_ORIGINS", "*"))
    )
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL)


settings = Settings()
