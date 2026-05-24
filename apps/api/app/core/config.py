"""Centralized application settings.

Settings come exclusively from environment variables (typically loaded from
`apps/api/.env`). Never read or write secrets anywhere else.

Validation policy:
    - Settings load even when LLM is unconfigured, so the API can still serve
      `/health` and `/llm/status` for diagnostics.
    - Provider-specific completeness is checked on demand via
      `Settings.missing_for_provider(...)`. The LLM factory enforces it when
      a real client is requested.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Directory of the api app (`apps/api/`). Used to resolve relative paths
#: like the default DATA_DIR (`../../data`) regardless of cwd.
API_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Process-wide configuration.

    Field names map to UPPER_SNAKE env vars (case-insensitive).
    Unknown env keys are ignored so the file stays forward-compatible.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    cors_allow_origins: str = Field(default="http://localhost:3000")
    data_dir: str = Field(default="../../data")

    llm_provider: str = Field(default="seed")

    seed_api_key: str | None = Field(default=None)
    seed_model: str | None = Field(default=None)
    seed_endpoint_id: str | None = Field(default=None)
    # Optional override; SeedClient supplies a sensible default when empty.
    seed_api_base_url: str | None = Field(default=None)

    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    def data_dir_path(self) -> Path:
        """Resolve DATA_DIR to an absolute Path.

        Absolute values are honored as-is; relative values are anchored to
        `apps/api/` so the result is the same no matter what cwd uvicorn
        was launched from.
        """
        p = Path(self.data_dir)
        if p.is_absolute():
            return p
        return (API_DIR / p).resolve()

    def missing_for_provider(self, provider: str | None = None) -> List[str]:
        """Return the env var names required for the given provider that
        are currently empty. Returns names only -- never values.

        Note: SEED_API_BASE_URL is optional and intentionally not listed.
        """
        provider = (provider or self.llm_provider).lower()

        if provider == "seed":
            required = {
                "SEED_API_KEY": self.seed_api_key,
                "SEED_MODEL": self.seed_model,
                "SEED_ENDPOINT_ID": self.seed_endpoint_id,
            }
            return [name for name, value in required.items() if not value]

        if provider == "mock":
            return []

        return [f"<unknown provider: {provider}>"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor so the .env file is read once per process."""
    return Settings()
