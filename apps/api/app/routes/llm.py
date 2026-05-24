"""LLM diagnostic routes.

Safe-by-design: never echoes API keys or any other secret. The status
endpoint returns only the provider name, a configured/not-configured
boolean, and the *names* of any missing env vars.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/llm", tags=["llm"])


class LLMStatusResponse(BaseModel):
    provider: str = Field(description="Active LLM_PROVIDER value.")
    configured: bool = Field(
        description="True iff every env var required by the provider is set."
    )
    missing_env_vars: List[str] = Field(
        default_factory=list,
        description="Names of env vars still empty for the active provider. "
        "Names only -- never values.",
    )
    supported_providers: List[str] = Field(
        default_factory=lambda: ["seed", "mock"],
        description="Providers this build of the API knows how to instantiate.",
    )


@router.get("/status", response_model=LLMStatusResponse)
def llm_status(settings: Settings = Depends(get_settings)) -> LLMStatusResponse:
    missing = settings.missing_for_provider()
    return LLMStatusResponse(
        provider=settings.llm_provider,
        configured=len(missing) == 0,
        missing_env_vars=missing,
    )
