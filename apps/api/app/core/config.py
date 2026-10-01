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
from typing import List, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Directory of the api app (`apps/api/`). Used to resolve relative paths
#: like the default DATA_DIR (`../../data`) regardless of cwd.
API_DIR = Path(__file__).resolve().parent.parent.parent

#: Repo root, two levels above `apps/api/`.
REPO_ROOT = API_DIR.parent.parent

#: Where prompt templates live.
PROMPTS_DIR = REPO_ROOT / "packages" / "prompts"

#: Remotion renderer app directory.
RENDERER_DIR = REPO_ROOT / "apps" / "renderer"


class Settings(BaseSettings):
    """Process-wide configuration.

    Field names map to UPPER_SNAKE env vars (case-insensitive).
    Unknown env keys are ignored so the file stays forward-compatible.
    """

    model_config = SettingsConfigDict(
        env_file=API_DIR / ".env",
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
    seed_thinking: Literal["enabled", "disabled"] | None = None
    # Optional override; SeedClient supplies a sensible default when empty.
    seed_api_base_url: str | None = Field(default=None)

    app_env: str = "development"
    legacy_local_api: bool = False
    cookie_secure: bool = False
    session_days: int = Field(default=7, ge=1, le=30)
    invite_quota: int = Field(default=3, ge=1)
    global_generation_limit: int = Field(default=10, ge=0)
    max_upload_mb: int = Field(default=30, ge=1, le=200)
    max_video_seconds: float = Field(default=30, gt=0, le=120)
    web_dist: str = str(REPO_ROOT / "apps/web/out")
    worker_enabled: bool = True
    database_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str = "doubao-embedding-vision-251215"
    embedding_api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    embedding_dimensions: int = 1024
    seedance_enabled: bool = False
    seedance_provider: str = "seedance"
    seedance_api_key: str | None = None
    seedance_model: str | None = None
    seedance_api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    seedance_global_limit: int = Field(default=2, ge=0)
    seedance_poll_seconds: float = Field(default=5, gt=0)
    seedance_timeout_seconds: int = Field(default=600, ge=1)

    def capabilities(self) -> dict:
        def state(required: dict, enabled: bool = True) -> dict:
            missing = [key for key, value in required.items() if not value]
            return {
                "enabled": enabled,
                "configured": not missing,
                "missing_env_vars": missing,
            }

        return {
            "planner": {
                **state({k: False for k in self.missing_for_provider()}),
                "provider": self.llm_provider,
            },
            "retrieval": state(
                {
                    "DATABASE_URL": self.database_url,
                    "EMBEDDING_API_KEY": self.embedding_api_key,
                    "EMBEDDING_MODEL": self.embedding_model,
                }
            ),
            "video": {
                **state(
                    (
                        {}
                        if self.seedance_provider == "mock"
                        else {
                            "SEEDANCE_API_KEY": self.seedance_api_key,
                            "SEEDANCE_MODEL": self.seedance_model,
                        }
                    ),
                    self.seedance_enabled,
                ),
                "provider": self.seedance_provider,
            },
        }

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
            }
            return [name for name, value in required.items() if not value]

        if provider == "mock":
            return []

        return [f"<unknown provider: {provider}>"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor so the .env file is read once per process."""
    return Settings()
