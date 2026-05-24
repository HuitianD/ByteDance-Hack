"""Pydantic schemas for video upload + analysis routes.

Mirrors the TS types in `packages/schemas` where applicable. Today only
the upload response is defined; analysis fields will be added when the
analyze endpoint lands.
"""

from __future__ import annotations

from datetime import datetime

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
