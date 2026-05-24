"""Pydantic schemas for video upload + analysis routes.

Keep field names snake_case on the API side. Mirrors of these models in
`packages/schemas` use camelCase per TS convention.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class VideoUploadResponse(BaseModel):
    """Returned by `POST /videos/upload`."""

    job_id: str = Field(description="Server-generated UUID identifying this upload.")
    original_filename: str = Field(description="Filename as provided by the client.")
    saved_path: str = Field(
        description="Path of the stored file, relative to DATA_DIR. "
        "Example: 'uploads/<job_id>/original.mp4'."
    )
    content_type: str = Field(description="MIME type reported by the client.")
    size_bytes: int = Field(ge=0, description="Final size on disk after writing.")
    created_at: datetime = Field(description="UTC timestamp when the file was saved.")


class FrameInfo(BaseModel):
    """One representative frame extracted from the source video."""

    index: int = Field(ge=0, description="Zero-based index in extraction order.")
    timestamp_seconds: float = Field(
        ge=0.0, description="Source video timestamp the frame was sampled at."
    )
    path: str = Field(
        description="Path to the saved JPEG, relative to DATA_DIR. "
        "Served at `<API>/static/<path>`."
    )


class SceneSegment(BaseModel):
    """A continuous range of the source video treated as one scene."""

    id: str = Field(description="Stable identifier within this analysis.")
    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(ge=0.0)
    role: Optional[str] = Field(
        default=None,
        description="Optional role label (hook, reveal, payoff, ...). "
        "Not populated by the basic analyzer.",
    )
    thumbnail_path: Optional[str] = Field(
        default=None,
        description="Optional thumbnail path relative to DATA_DIR.",
    )


class VideoAnalysis(BaseModel):
    """Returned by `POST /videos/{job_id}/analyze-basic`.

    Also persisted to `data/knowledge_base/<job_id>/video_analysis.json`.
    """

    id: str = Field(description="UUID for this analysis run.")
    job_id: str = Field(description="Upload job_id this analysis is for.")
    source_video_path: str = Field(
        description="Source video path, relative to DATA_DIR."
    )
    duration_seconds: float = Field(ge=0.0)
    fps: float = Field(ge=0.0)
    width: int = Field(ge=0)
    height: int = Field(ge=0)
    total_frames: int = Field(ge=0)
    file_size_bytes: int = Field(ge=0)
    frames: List[FrameInfo] = Field(
        default_factory=list,
        description="Representative frames extracted from the source video.",
    )
    scenes: List[SceneSegment] = Field(
        default_factory=list,
        description="Detected or time-based scene segments.",
    )
    scene_detection_method: str = Field(
        description="'pyscenedetect' if real detection ran, else 'time_based'."
    )
    created_at: datetime = Field(description="UTC timestamp when analysis completed.")
