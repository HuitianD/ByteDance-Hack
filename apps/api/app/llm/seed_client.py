"""ByteDance Seed (AIGC) LLM client.

Skeleton implementation. The transport, auth header, and base URL pattern
are wired up so the rest of the app can depend on this class today, but the
exact request payload and response parsing are intentionally left as TODO
sections. Fill them in from the official Seed API docs you have access to.

Why a skeleton instead of a guess:
    Seed/Volcano endpoints differ between deployments (region, model family,
    OpenAI-compatible vs. native schema). Hardcoding one shape now would
    almost certainly need to be undone. The TODOs mark the exact spots to
    edit when you have the official spec.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

import httpx

from .base import LLMClient, LLMConfigError, LLMError


#: Default base URL when SEED_API_BASE_URL is not set.
#: Volcano Ark cn-beijing endpoint -- override via env if your deployment
#: uses a different region or host.
DEFAULT_SEED_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


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
    ) -> None:
        if not api_key:
            raise LLMConfigError("SEED_API_KEY is required for SeedClient")
        if not model:
            raise LLMConfigError("SEED_MODEL is required for SeedClient")
        if not endpoint_id:
            raise LLMConfigError("SEED_ENDPOINT_ID is required for SeedClient")

        effective_base_url = (base_url or DEFAULT_SEED_BASE_URL).rstrip("/")

        self._model = model
        self._endpoint_id = endpoint_id
        self._http = httpx.AsyncClient(
            base_url=effective_base_url,
            timeout=timeout_seconds,
            headers={
                # ----------------------------------------------------------
                # TODO(seed-auth): confirm the auth header expected by your
                # Seed deployment. Common shapes:
                #   "Authorization": f"Bearer {api_key}"
                #   "X-Api-Key": api_key
                # Replace this line if the official docs require something
                # different.
                # ----------------------------------------------------------
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
        payload = self._build_payload(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object", "schema": schema_hint},
        )
        data = await self._post_chat(payload)
        text = self._extract_text(data)
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
    # Internals -- fill in TODOs against the official Seed API spec.
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
        """Construct the request body.

        TODO(seed-payload): replace this body with the exact schema the
        Seed API expects. The OpenAI-compatible `messages[]` shape below is
        a placeholder; some Seed endpoints use `input`, `prompt`, or a
        provider-native schema. Keep the function pure -- transport stays
        in `_post_chat`.

        TODO(seed-model-vs-endpoint): Volcano Ark commonly uses the
        endpoint id (EP) as the value of the `model` field. If your
        deployment expects that, use `self._endpoint_id` instead of
        `self._model` below. If it expects both (model name + EP), add an
        extra field per the official spec.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body: dict[str, Any] = {
            "model": self._model,  # or self._endpoint_id -- see TODO above
            "messages": messages,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        if response_format is not None:
            body["response_format"] = response_format
        return body

    async def _post_chat(self, payload: Mapping[str, Any]) -> Any:
        """Send the request and return the decoded JSON response.

        TODO(seed-endpoint): set the correct path. Common values:
            "/chat/completions"        (Volcano Ark, OpenAI-compatible)
            "/v3/chat/completions"
            "/api/v3/chat/completions"
        Use the path documented for the model family you are targeting.
        """
        path = "/chat/completions"  # TODO(seed-endpoint)
        try:
            resp = await self._http.post(path, json=dict(payload))
        except httpx.HTTPError as exc:
            raise LLMError(f"Seed transport error: {exc}") from exc

        if resp.status_code >= 400:
            # Body may contain useful diagnostics; keep it short.
            snippet = resp.text[:500] if resp.text else ""
            raise LLMError(
                f"Seed returned HTTP {resp.status_code}: {snippet}"
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise LLMError(f"Seed response was not JSON: {exc}") from exc

    @staticmethod
    def _extract_text(data: Any) -> str:
        """Pull the assistant's text out of the response.

        TODO(seed-response): adjust to match the official response schema.
        Defaults to OpenAI-compatible `choices[0].message.content`.
        """
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
