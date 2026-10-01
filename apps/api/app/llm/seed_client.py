"""ByteDance Seed planner using the Ark chat-completions endpoint."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

import httpx

from .base import LLMClient, LLMConfigError, LLMError


#: Default base URL when SEED_API_BASE_URL is not set.
#: Volcano Ark cn-beijing endpoint -- override via env if your deployment
#: uses a different region or host.
DEFAULT_SEED_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


_FENCE_OPEN_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*")
_FENCE_CLOSE_RE = re.compile(r"\s*```\s*$")


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` (or plain ```) wrappers some models emit.

    Doubao-Lite, without `response_format`, usually obeys the "no markdown
    fences" instruction but occasionally still wraps the JSON. We strip
    defensively; non-fenced inputs pass through unchanged.
    """
    s = text.strip()
    if not s.startswith("```"):
        return s
    s = _FENCE_OPEN_RE.sub("", s, count=1)
    s = _FENCE_CLOSE_RE.sub("", s, count=1)
    return s.strip()


class SeedClient(LLMClient):
    provider_name = "seed"

    def __init__(
        self,
        api_key: str,
        model: str,
        endpoint_id: str,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
        thinking: str | None = None,
    ) -> None:
        if not api_key:
            raise LLMConfigError("SEED_API_KEY is required for SeedClient")
        if not model:
            raise LLMConfigError("SEED_MODEL is required for SeedClient")
        if not endpoint_id:
            raise LLMConfigError("SEED_ENDPOINT_ID is required for SeedClient")

        effective_base_url = (base_url or DEFAULT_SEED_BASE_URL).rstrip("/")

        self.last_usage = {}
        self._model = model
        self._endpoint_id = endpoint_id
        self._thinking = thinking
        self._http = httpx.AsyncClient(
            base_url=effective_base_url,
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        payload = self._build_payload(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=None,
        )
        data = await self._post_chat(payload)
        return self._extract_text(data)

    async def generate_json(
        self,
        prompt: str,
        *,
        schema_hint: Mapping[str, Any] | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        # Doubao-Seed-Lite rejects `response_format=json_object` (HTTP 400
        # InvalidParameter). Schema is already embedded in the prompt
        # templates and the system message requires raw JSON, so we omit
        # the field and validate after parsing. `schema_hint` is kept in
        # the signature for forward-compat with models that accept it.
        _ = schema_hint
        payload = self._build_payload(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=None,
        )
        data = await self._post_chat(payload)
        text = _strip_code_fences(self._extract_text(data))
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(
                f"Seed returned non-JSON content for generate_json: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise LLMError("Seed JSON response did not parse to an object")
        return parsed

    # ------------------------------------------------------------------
    # Transport and response parsing.
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        *,
        prompt: str,
        system: str | None,
        max_tokens: int | None,
        temperature: float | None,
        response_format: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """Construct the Ark chat-completions request using the configured endpoint ID."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body: dict[str, Any] = {
            # Ark accepts a public Model ID or a configured endpoint (EP).
            # The factory prefers an explicit EP, otherwise uses SEED_MODEL.
            "model": self._endpoint_id,
            "messages": messages,
        }
        body["max_tokens"] = max_tokens if max_tokens is not None else 4096
        if self._thinking is not None:
            body["thinking"] = {"type": self._thinking}
        if temperature is not None:
            body["temperature"] = temperature
        if response_format is not None:
            body["response_format"] = response_format
        return body

    async def _post_chat(self, payload: Mapping[str, Any]) -> Any:
        """Send one request; callers explicitly decide whether to retry."""
        path = "/chat/completions"
        try:
            resp = await self._http.post(path, json=dict(payload))
        except httpx.HTTPError as exc:
            raise LLMError(f"Seed transport error: {exc}") from exc

        if resp.status_code >= 400:
            # Body may contain useful diagnostics; keep it short.
            snippet = resp.text[:500] if resp.text else ""
            raise LLMError(f"Seed returned HTTP {resp.status_code}: {snippet}")
        try:
            data = resp.json()
            self.last_usage = data.get("usage", {})
            return data
        except ValueError as exc:
            raise LLMError(f"Seed response was not JSON: {exc}") from exc

    @staticmethod
    def _extract_text(data: Any) -> str:
        """Read the assistant content from an Ark chat response."""
        try:
            choices = data["choices"]
            content = choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                "Could not find assistant content in Seed response. "
                "Update SeedClient._extract_text to match the actual schema."
            ) from exc
        if not isinstance(content, str):
            raise LLMError("Seed response content was not a string")
        return content
