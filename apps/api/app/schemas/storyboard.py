"""Storyboard schemas.

A Storyboard is the contract between the AI generation step and the
Remotion renderer. Each scene carries enough structured fields to drive a
deterministic composition.

TS canonical mirror: `packages/schemas/src/storyboard.ts`.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


#: Default canvas. Vertical 9:16 short-form. Override later if needed.
DEFAULT_FPS: int = 30
DEFAULT_WIDTH: int = 1080
DEFAULT_HEIGHT: int = 1920


class StoryboardScene(BaseModel):
    """One ordered scene in the storyboard."""

    model_config = ConfigDict(extra="ignore")

    scene_id: str
    start_time: float = Field(ge=0.0, description="Seconds into the storyboard.")
    end_time: float = Field(ge=0.0, description="Seconds into the storyboard.")
    duration_seconds: float = Field(ge=0.0)

    layout: str = Field(
        description="Layout token consumed by the renderer "
        "(e.g. 'centered-text', 'fullscreen-asset', 'split', 'lower-third-caption')."
    )
    text: Optional[str] = Field(
        default=None, description="Optional on-screen text."
    )
    visual_description: str = Field(
        description="Plain-language description of what the scene should show. "
        "Used by humans + by future asset generation."
    )
    animation: Optional[str] = Field(
        default=None,
        description="Animation token applied to the scene's primary element.",
    )
    transition: Optional[str] = Field(
        default=None,
        description="Transition into this scene (e.g. 'cut', 'fade', 'slide').",
    )
    asset_prompt: Optional[str] = Field(
        default=None,
        description="Prompt for generating the visual asset for this scene.",
    )

    source_structure_card_id: Optional[str] = Field(
        default=None,
        description="StructureCard id this scene was derived from.",
    )
    source_editing_atoms: List[str] = Field(
        default_factory=list,
        description="Editing-atom kinds (e.g. 'hook', 'reveal') referenced by this scene.",
    )


class Storyboard(BaseModel):
    """Returned by `POST /storyboards/generate` and persisted to disk."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="UUID for this storyboard.")
    title: str = Field(description="Short title; LLM-generated from the user prompt.")
    user_prompt: str = Field(description="The original user request / brief.")
    target_duration_seconds: float = Field(ge=0.0)
    actual_duration_seconds: float = Field(
        ge=0.0,
        description="Sum of scene durations after normalization.",
    )

    fps: int = Field(default=DEFAULT_FPS, ge=1)
    width: int = Field(default=DEFAULT_WIDTH, ge=1)
    height: int = Field(default=DEFAULT_HEIGHT, ge=1)

    scenes: List[StoryboardScene] = Field(default_factory=list)

    source_structure_card_ids: List[str] = Field(
        default_factory=list,
        description="StructureCards the generator was given as references.",
    )

    created_at: datetime = Field(description="UTC timestamp.")


class StoryboardGenerateRequest(BaseModel):
    """Body for `POST /storyboards/generate`."""

    model_config = ConfigDict(extra="forbid")

    user_prompt: str = Field(min_length=1, max_length=2000)
    target_duration_seconds: float = Field(default=20.0, ge=2.0, le=120.0)
    source_job_ids: Optional[List[str]] = Field(
        default=None,
        description="If set, use these jobs' structure cards. Otherwise the most "
        "recent 1-3 cards on disk are used.",
    )
