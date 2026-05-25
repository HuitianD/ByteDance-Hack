"""RenderJob schema.

Tracks one render of a Storyboard into an mp4 file.

For MVP the route is synchronous: we only return the job once it has either
succeeded or failed. The schema still uses a `status` enum so we can later
evolve to async/queued rendering without breaking the contract.

TS canonical mirror: `packages/schemas/src/renderJob.ts`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RenderJobStatus = Literal[
    "queued", "running", "succeeded", "failed", "cancelled"
]


class RenderMediaSummary(BaseModel):
    """Compact summary of which source media was used to render the mp4.

    Surfaced on `RenderJob.media_summary` so the UI can tell the user
    whether the output used the uploaded video, extracted frames, or
    fell back to the placeholder visuals.
    """

    model_config = ConfigDict(extra="ignore")

    used_source_video: bool = Field(
        description="True when the uploaded original.* was passed to Remotion."
    )
    used_frames: bool = Field(
        description="True when at least one extracted frame was passed in."
    )
    frame_count: int = Field(
        ge=0, description="Number of representative frames bundled."
    )
    source_job_id: Optional[str] = Field(
        default=None,
        description="job_id whose upload + frames were reused, if any.",
    )
    placeholder_only: bool = Field(
        description=(
            "True when no real media was resolved and the renderer ran in "
            "premium-gradient placeholder mode."
        ),
    )


class RenderJob(BaseModel):
    """Returned by `POST /storyboards/{id}/render`."""

    model_config = ConfigDict(extra="ignore")

    render_job_id: str = Field(description="UUID for this render attempt.")
    storyboard_id: str
    status: RenderJobStatus

    output_path: Optional[str] = Field(
        default=None,
        description="Path to the rendered mp4 *relative to DATA_DIR* "
        "(e.g. 'renders/<storyboard_id>/final.mp4').",
    )
    output_url: Optional[str] = Field(
        default=None,
        description="Server-absolute URL path to the rendered mp4 "
        "(e.g. '/static/renders/<storyboard_id>/final.mp4'). "
        "Frontend prepends the API base URL.",
    )

    duration_ms: Optional[int] = Field(
        default=None, description="How long the render took, in ms."
    )
    error: Optional[str] = Field(
        default=None,
        description="Last few lines of the renderer's stderr if status='failed'.",
    )

    media_summary: Optional[RenderMediaSummary] = Field(
        default=None,
        description=(
            "Compact summary of the media reused for this render "
            "(source video / extracted frames / placeholder-only)."
        ),
    )

    created_at: datetime = Field(description="UTC timestamp when the job started.")
