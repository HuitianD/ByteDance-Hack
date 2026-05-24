"""Mock LLM client.

Useful for local development and tests when no API key is configured.
Set `LLM_PROVIDER=mock` in `.env` to activate.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from .base import LLMClient


class MockClient(LLMClient):
    provider_name = "mock"

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        return f"[mock] received {len(prompt)} chars"

    async def generate_json(
        self,
        prompt: str,
        *,
        schema_hint: Mapping[str, Any] | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "echo": prompt[:200],
            "schema_hint_keys": sorted(list(schema_hint.keys())) if schema_hint else [],
        }
