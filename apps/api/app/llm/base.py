"""Provider-agnostic LLM client interface.

Product code should depend only on `LLMClient` and obtain instances from
`app.llm.factory.get_llm_client`. This keeps Seed (or any future provider)
swappable without touching analysis / generation logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class LLMError(RuntimeError):
    """Raised when an LLM call fails (network, auth, server error, etc.)."""


class LLMConfigError(LLMError):
    """Raised when an LLM client is requested but config is incomplete."""


class LLMClient(ABC):
    """Abstract base for all LLM providers.

    Implementations must be safe to use from FastAPI request handlers.
    Methods are async so providers can use httpx.AsyncClient natively.
    """

    #: Stable identifier used by `/llm/status` and logs. Override in subclass.
    provider_name: str = "abstract"

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Return a plain text completion for `prompt`."""

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        *,
        schema_hint: Mapping[str, Any] | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Return a parsed JSON object for `prompt`.

        `schema_hint` is an optional JSON-Schema-like dict that the
        implementation may use to steer the model's output. The default
        implementation calls `generate_text` and parses the result, but
        providers can override to use native JSON-mode features.
        """

    async def aclose(self) -> None:
        """Release any underlying resources (e.g. HTTP client)."""
        return None
