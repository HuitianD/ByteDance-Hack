"""Video upload + basic analysis routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.llm.base import LLMConfigError, LLMError
from app.llm.factory import get_llm_client
from app.schemas.structure_card import StructureCard
from app.schemas.video import VideoAnalysis, VideoUploadResponse
from app.services.structure_card import (
    StructureCardValidationError,
    extract_structure_card,
)
from app.services.video_analysis import AnalysisError, analyze_video_file

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
        pass


def _validate_job_id(job_id: str) -> str:
    """Reject non-UUID job_ids to prevent path traversal in lookups."""
    try:
        return str(uuid.UUID(job_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job_id '{job_id}' (must be a UUID).",
        ) from exc


def _find_uploaded_video(data_dir: Path, job_id: str) -> Path:
    """Return the path to the original video for a given job_id.

    Raises HTTPException(404) when the job or video is missing.
    """
    upload_dir = data_dir / "uploads" / job_id
    if not upload_dir.exists() or not upload_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    candidates = sorted(upload_dir.glob("original.*"))
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Original video not found for job '{job_id}'.",
        )
    return candidates[0]


# ---------------------------------------------------------------------------
# POST /videos/upload
# ---------------------------------------------------------------------------


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
    except Exception as exc:  # noqa: BLE001
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


# ---------------------------------------------------------------------------
# POST /videos/{job_id}/analyze-basic
# ---------------------------------------------------------------------------


@router.post(
    "/{job_id}/analyze-basic",
    response_model=VideoAnalysis,
    summary="Run basic, deterministic, non-LLM video analysis",
)
def analyze_basic(
    job_id: str,
    settings: Settings = Depends(get_settings),
) -> VideoAnalysis:
    """Extract metadata, representative frames, and scene segments.

    Side effects (idempotent on re-run):
        - Wipes and rewrites `data/frames/<job_id>/`.
        - Writes `data/knowledge_base/<job_id>/video_analysis.json`.

    Defined as a sync function so FastAPI runs it in a threadpool: OpenCV
    and PySceneDetect are blocking.
    """
    job_id = _validate_job_id(job_id)

    data_dir = settings.data_dir_path()
    video_path = _find_uploaded_video(data_dir, job_id)

    try:
        analysis = analyze_video_file(
            job_id=job_id,
            video_path=video_path,
            data_dir=data_dir,
        )
    except AnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    kb_dir = data_dir / "knowledge_base" / job_id
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "video_analysis.json").write_text(
        analysis.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return analysis


# ---------------------------------------------------------------------------
# POST /videos/{job_id}/extract-structure-card
# ---------------------------------------------------------------------------


def _load_video_analysis(data_dir: Path, job_id: str) -> VideoAnalysis:
    analysis_path = data_dir / "knowledge_base" / job_id / "video_analysis.json"
    if not analysis_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"video_analysis.json not found for job '{job_id}'. "
                "Run POST /videos/{job_id}/analyze-basic first."
            ),
        )
    try:
        return VideoAnalysis.model_validate_json(analysis_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 -- corrupt or stale JSON
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse video_analysis.json for job '{job_id}': {exc}",
        ) from exc


@router.post(
    "/{job_id}/extract-structure-card",
    response_model=StructureCard,
    summary="Build a reusable StructureCard from VideoAnalysis (uses LLM adapter)",
)
async def extract_structure_card_route(
    job_id: str,
    settings: Settings = Depends(get_settings),
) -> StructureCard:
    job_id = _validate_job_id(job_id)

    data_dir = settings.data_dir_path()

    # 404 if upload dir is missing entirely; cleaner error than "no analysis".
    if not (data_dir / "uploads" / job_id).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    analysis = _load_video_analysis(data_dir, job_id)

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
            card = await extract_structure_card(analysis, client)
        except StructureCardValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "LLM returned a payload that did not validate "
                    "as a StructureCard.",
                    "errors": exc.args[0] if exc.args else [],
                },
            ) from exc
        except LLMError as exc:
            detail = f"LLM call failed: {exc}"
            if "HTTP 401" in str(exc) or "AuthenticationError" in str(exc):
                detail = (
                    "Seed rejected the API key (HTTP 401). "
                    "Verify SEED_API_KEY in apps/api/.env matches your Volcano "
                    "Ark console, or set LLM_PROVIDER=mock and restart the API."
                )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            ) from exc
    finally:
        await client.aclose()

    out_path = data_dir / "knowledge_base" / job_id / "structure_card.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(card.model_dump_json(indent=2), encoding="utf-8")

    return card
