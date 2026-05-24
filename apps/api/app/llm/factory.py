"""LLM client factory.

Single entry point for building an `LLMClient` from `Settings`. Product
code should depend only on this and on `LLMClient`, never on a concrete
provider class.
"""

from __future__ import annotations

from app.core.config import Settings, get_settings

from .base import LLMClient, LLMConfigError
from .mock_client import MockClient
from .seed_client import SeedClient


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider == "seed":
        missing = settings.missing_for_provider("seed")
        if missing:
            raise LLMConfigError(
                "Seed LLM provider is not fully configured. "
                f"Missing env vars: {', '.join(missing)}. "
                "Add them to apps/api/.env."
            )
        return SeedClient(
            api_key=settings.seed_api_key or "",
            model=settings.seed_model or "",
            endpoint_id=settings.seed_endpoint_id or "",
            base_url=settings.seed_api_base_url or None,
        )

    if provider == "mock":
        return MockClient()

    raise LLMConfigError(
        f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
        "Supported values: seed, mock."
    )
