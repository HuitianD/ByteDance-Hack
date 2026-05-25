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

    created_at: datetime = Field(description="UTC timestamp when the job started.")
