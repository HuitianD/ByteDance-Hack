"""Storyboard generation + render routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core.config import Settings, get_settings
from app.llm.base import LLMConfigError, LLMError
from app.llm.factory import get_llm_client
from app.schemas.render_job import RenderJob
from app.schemas.storyboard import Storyboard, StoryboardGenerateRequest
from app.services.render import (
    RenderError,
    RendererSetupError,
    render_storyboard,
)
from app.services.storyboard import (
    CardSelectionError,
    StoryboardValidationError,
    generate_storyboard,
    persist_storyboard,
    select_structure_cards,
)

router = APIRouter(prefix="/storyboards", tags=["storyboards"])


def _validate_storyboard_id(storyboard_id: str) -> None:
    try:
        uuid.UUID(storyboard_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid storyboard_id '{storyboard_id}' (must be a UUID).",
        ) from exc


@router.post(
    "/generate",
    response_model=Storyboard,
    summary="Generate a Storyboard from a user prompt + saved StructureCards",
)
async def generate_storyboard_route(
    body: StoryboardGenerateRequest,
    settings: Settings = Depends(get_settings),
) -> Storyboard:
    data_dir = settings.data_dir_path()

    try:
        cards = select_structure_cards(
            data_dir=data_dir,
            source_job_ids=body.source_job_ids,
        )
    except CardSelectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    try:
        client = get_llm_client(settings)
    except LLMConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"LLM provider not configured: {exc} "
                "Either fix apps/api/.env or set LLM_PROVIDER=mock for testing."
            ),
        ) from exc

    try:
        try:
            storyboard = await generate_storyboard(
                user_prompt=body.user_prompt,
                target_duration_seconds=body.target_duration_seconds,
                cards=cards,
                llm_client=client,
            )
        except StoryboardValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "LLM returned a payload that did not validate "
                    "as a Storyboard.",
                    "errors": exc.args[0] if exc.args else [],
                },
            ) from exc
        except LLMError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM call failed: {exc}",
            ) from exc
    finally:
        await client.aclose()

    persist_storyboard(data_dir, storyboard)

    return storyboard


@router.post(
    "/{storyboard_id}/render",
    response_model=RenderJob,
    summary="Render a saved Storyboard into an mp4 via Remotion",
)
async def render_storyboard_route(
    storyboard_id: str = Path(..., description="UUID of a saved storyboard."),
    settings: Settings = Depends(get_settings),
) -> RenderJob:
    _validate_storyboard_id(storyboard_id)
    data_dir = settings.data_dir_path()

    try:
        return await render_storyboard(
            storyboard_id=storyboard_id,
            data_dir=data_dir,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RendererSetupError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Renderer not ready: {exc} "
                "Run `npm install --workspace apps/renderer` from the repo root."
            ),
        ) from exc
    except RenderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Render subprocess failed.",
                "error": str(exc),
                "stderr_tail": exc.stderr_tail,
            },
        ) from exc
