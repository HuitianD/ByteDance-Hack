"""Video upload + (later) analysis routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.schemas.video import VideoUploadResponse

router = APIRouter(prefix="/videos", tags=["videos"])

#: Hard cap on upload size. Tune via env later if needed.
MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB

#: Streamed write chunk size.
_CHUNK_SIZE = 1024 * 1024  # 1 MB

#: Extensions we'll accept. content_type check is the primary gate; this is
#: only used to pick a sensible suffix for the saved file.
_KNOWN_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".mpeg", ".mpg"}


def _safe_extension(filename: str | None, content_type: str) -> str:
    """Pick a file extension to save under.

    Prefers the original filename's extension when it's a known video
    extension. Falls back to a content-type guess, then `.mp4`.
    """
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix in _KNOWN_VIDEO_EXTS:
            return suffix
    # Last-resort guess from content type.
    if "/" in content_type:
        subtype = content_type.split("/", 1)[1].lower()
        guess = f".{subtype}"
        if guess in _KNOWN_VIDEO_EXTS:
            return guess
        if subtype in {"quicktime"}:
            return ".mov"
    return ".mp4"


def _cleanup(path: Path, parent_dir: Path) -> None:
    """Best-effort removal of a partial upload."""
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
    try:
        parent_dir.rmdir()
    except OSError:
        # Directory not empty or already gone -- fine.
        pass


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a sample video",
)
async def upload_video(
    file: UploadFile = File(..., description="Video file to upload"),
    settings: Settings = Depends(get_settings),
) -> VideoUploadResponse:
    content_type = file.content_type or ""
    if not content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type '{content_type or 'unknown'}'. "
            "File must be a video (content-type starting with 'video/').",
        )

    job_id = str(uuid.uuid4())
    suffix = _safe_extension(file.filename, content_type)

    data_dir = settings.data_dir_path()
    target_dir = data_dir / "uploads" / job_id
    target_path = target_dir / f"original{suffix}"

    target_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    try:
        with target_path.open("wb") as out:
            while True:
                chunk = await file.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
                    )
                out.write(chunk)
    except HTTPException:
        _cleanup(target_path, target_dir)
        raise
    except Exception as exc:  # noqa: BLE001 -- unexpected I/O errors -> 500
        _cleanup(target_path, target_dir)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save upload: {exc}",
        ) from exc
    finally:
        await file.close()

    saved_relative = target_path.relative_to(data_dir).as_posix()

    return VideoUploadResponse(
        job_id=job_id,
        original_filename=file.filename or "",
        saved_path=saved_relative,
        content_type=content_type,
        size_bytes=total_bytes,
        created_at=datetime.now(timezone.utc),
    )
