from __future__ import annotations
import asyncio
import shutil
import time
import uuid
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from app.core.config import API_DIR
from app.runtime.store import StoreError
from app.schemas.workspace import (
    Invitation,
    JobSubmit,
    JobView,
    SearchRequest,
    Feedback,
)
from app.schemas.storyboard import Storyboard, StoryboardEdit
from app.services.editor import edit_storyboard
from app.services.storyboard import persist_storyboard
from app.services.video_analysis import _read_metadata
from app.routes.videos import _safe_extension

router = APIRouter(prefix="/api")
COOKIE = "viralcraft_session"


def state(request: Request):
    return request.app.state


def session(request: Request):
    return state(request).store.session(request.cookies.get(COOKIE))


@router.get("/status")
def status(request: Request) -> dict:
    return state(request).settings.capabilities()


@router.post("/session")
def redeem(body: Invitation, request: Request, response: Response) -> dict:
    s = state(request)
    token, owner = s.store.redeem(body.code, s.settings.session_days)
    response.set_cookie(
        COOKIE,
        token,
        max_age=s.settings.session_days * 86400,
        httponly=True,
        secure=s.settings.cookie_secure or s.settings.app_env == "production",
        samesite="lax",
        path="/",
    )
    return {
        "authenticated": True,
        "quota": s.store.session(token)["quota"],
        "used": s.store.usage(owner),
    }


@router.get("/session")
def whoami(request: Request, user=Depends(session)) -> dict:
    return {
        "authenticated": True,
        "quota": user["quota"],
        "used": state(request).store.usage(user["id"]),
    }


@router.get("/workspace")
def workspace(request: Request, user=Depends(session)) -> dict:
    store = state(request).store
    owner = user["id"]
    return {
        k: store.resources(owner, v)
        for k, v in [
            ("uploads", "upload"),
            ("storyboards", "storyboard"),
            ("renders", "render"),
            ("audio", "audio"),
        ]
    } | {"jobs": store.jobs(owner)}


@router.get("/library")
def library(request: Request) -> dict:
    try:
        owner = session(request)["id"]
    except StoreError:
        owner = ""
    return {
        "cards": state(request).store.resources(owner, "card", True),
        "mode": "manual",
    }


@router.post("/library/search")
async def search(body: SearchRequest, request: Request, user=Depends(session)) -> dict:
    from app.services.retrieval import search_cards

    s = state(request)
    return await search_cards(s.settings, s.store, user, body.query)


@router.post("/videos/upload", status_code=201)
async def upload(
    request: Request, file: UploadFile = File(...), user=Depends(session)
) -> dict:
    s = state(request)
    owner = user["id"]
    d = s.settings.data_dir_path()
    s.store.reserve(
        owner, "upload", user["quota"] * 4, s.settings.global_generation_limit * 4
    )
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(415, "Upload a video file.")
    rid = str(uuid.uuid4())
    folder = d / "uploads" / rid
    folder.mkdir(parents=True)
    path = folder / (
        "original" + _safe_extension(file.filename, file.content_type or "")
    )
    total = 0
    try:
        with path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > s.settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(413, "Video exceeds the upload size limit.")
                out.write(chunk)
        meta = await asyncio.to_thread(_read_metadata, path)
        if (
            meta.duration_seconds > s.settings.max_video_seconds
            or meta.width * meta.height > 3840 * 2160
        ):
            raise HTTPException(422, "Use a video up to 30 seconds and 4K resolution.")
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            422, "This video cannot be decoded. Try an H.264 MP4."
        ) from exc
    finally:
        await file.close()
    body = {
        "id": rid,
        "job_id": rid,
        "original_filename": file.filename or "video.mp4",
        "saved_path": path.relative_to(d).as_posix(),
        "content_type": file.content_type,
        "size_bytes": total,
        "duration_seconds": meta.duration_seconds,
        "created_at": time.time(),
        "url": f"/api/media/{rid}",
    }
    s.store.put_resource(owner, "upload", body)
    return body


@router.post("/audio/upload", status_code=201)
async def upload_audio(
    request: Request, file: UploadFile = File(...), user=Depends(session)
) -> dict:
    s = state(request)
    s.store.reserve(user["id"], "audio", 3, s.settings.global_generation_limit * 2)
    if not (file.content_type or "").startswith("audio/"):
        raise HTTPException(415, "Upload an MP3 or WAV audio file.")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp3", ".wav", ".m4a"}:
        raise HTTPException(415, "Use MP3, WAV or M4A.")
    rid = str(uuid.uuid4())
    path = s.settings.data_dir_path() / "audio" / (rid + suffix)
    path.parent.mkdir(exist_ok=True)
    try:
        content = await file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Audio must be under 10 MB.")
        path.write_bytes(content)
        from app.services.probe import probe_media

        meta = await probe_media(path)
        if not any(
            stream.get("codec_type") == "audio" for stream in meta.get("streams", [])
        ):
            raise ValueError("No audio")
    except Exception as exc:
        path.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(422, "The audio cannot be decoded.") from exc
    finally:
        await file.close()
    body = {
        "id": rid,
        "path": path.relative_to(s.settings.data_dir_path()).as_posix(),
        "name": file.filename,
        "url": f"/api/media/{rid}",
    }
    return s.store.put_resource(user["id"], "audio", body)


@router.post("/demo", status_code=201)
def demo(request: Request, user=Depends(session)) -> dict:
    s = state(request)
    s.store.reserve(
        user["id"], "upload", user["quota"] * 4, s.settings.global_generation_limit * 4
    )
    source = API_DIR / "demo/sample.mp4"
    if not source.exists():
        raise HTTPException(
            503, "Demo footage is not installed. Upload your own video."
        )
    rid = str(uuid.uuid4())
    out = s.settings.data_dir_path() / "uploads" / rid / "original.mp4"
    out.parent.mkdir(parents=True)
    shutil.copy2(source, out)
    return s.store.put_resource(
        user["id"],
        "upload",
        {
            "id": rid,
            "job_id": rid,
            "original_filename": "ViralCraft demo — synthetic coffee product.mp4",
            "saved_path": out.relative_to(s.settings.data_dir_path()).as_posix(),
            "content_type": "video/mp4",
            "size_bytes": out.stat().st_size,
            "duration_seconds": 15,
            "created_at": time.time(),
            "url": f"/api/media/{rid}",
        },
    )


@router.get("/storyboards/{rid}")
def get_board(rid: str, request: Request, user=Depends(session)) -> Storyboard:
    return Storyboard.model_validate(
        state(request).store.resource(user["id"], rid, "storyboard")
    )


@router.patch("/storyboards/{rid}")
def patch_board(
    rid: str, body: StoryboardEdit, request: Request, user=Depends(session)
) -> Storyboard:
    s = state(request)
    board = Storyboard.model_validate(s.store.resource(user["id"], rid, "storyboard"))
    if body.audio_asset_id:
        s.store.resource(user["id"], body.audio_asset_id, "audio")
    if board.version != body.version:
        raise HTTPException(409, "This draft changed. Reload before saving.")
    try:
        updated = edit_storyboard(board, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    s.store.put_resource(
        user["id"],
        "storyboard",
        updated.model_dump(mode="json"),
        expected_version=body.version,
    )
    persist_storyboard(s.settings.data_dir_path(), updated)
    s.store.event(
        user["id"], "storyboard_edited", {"id": rid, "version": updated.version}
    )
    return updated


@router.post("/jobs", status_code=202, response_model=JobView)
def submit(body: JobSubmit, request: Request, user=Depends(session)):
    s = state(request)
    owner = user["id"]
    p = body.model_dump(mode="json", exclude_none=True)
    if body.kind in ("learn", "generate") and s.settings.missing_for_provider():
        raise HTTPException(503, "Planning model configuration is incomplete.")
    if body.kind in ("analyze", "learn"):
        s.store.resource(owner, str(body.resource_id), "upload")
    elif body.kind == "generate":
        b = body.storyboard
        if (
            not b
            or not b.target_media_job_id
            or not b.reference_card_ids
            or len(b.reference_card_ids) > 3
        ):
            raise HTTPException(
                422, "Select 1–3 reference cards and your target video."
            )
        if b.target_duration_seconds not in (15, 20):
            raise HTTPException(422, "Choose 15 or 20 seconds.")
        for cid in b.reference_card_ids:
            s.store.resource(owner, cid, "card", True)
        s.store.resource(owner, b.target_media_job_id, "upload")
    elif body.kind in ("render", "assets"):
        board = s.store.resource(owner, str(body.resource_id), "storyboard")
        if body.version != board["version"]:
            raise HTTPException(409, "Reload the latest draft before continuing.")
        s.store.resource(owner, board.get("target_media_job_id", ""), "upload")
        p["snapshot"] = board
        if body.kind == "assets":
            if not s.settings.seedance_enabled:
                raise HTTPException(
                    503,
                    "Video generation is disabled. You can still export your footage.",
                )
            if not 1 <= len(set(body.scene_ids)) == len(body.scene_ids) <= 2:
                raise HTTPException(422, "Choose one or two scenes.")
            if not set(body.scene_ids).issubset(
                {x["scene_id"] for x in board["scenes"]}
            ):
                raise HTTPException(422, "Unknown scene.")
            if body.reference_frame_id:
                frame = s.store.resource(owner, str(body.reference_frame_id), "frame")
                if frame["upload_id"] != board["target_media_job_id"]:
                    raise HTTPException(422, "Select a frame from the target video.")
                if not body.reference_has_no_faces:
                    raise HTTPException(
                        422,
                        "Confirm the selected product frame contains no real faces.",
                    )
    return s.store.enqueue(
        owner,
        body.kind,
        p,
        user["quota"],
        s.settings.global_generation_limit,
        s.settings.seedance_global_limit,
    )


@router.post("/jobs/{jid}/retry", status_code=202, response_model=JobView)
def retry(jid: str, request: Request, user=Depends(session)):
    # Reuse all validation and transactional quota checks, including fresh ownership.
    payload = state(request).store.retry_payload(user["id"], jid)
    return submit(JobSubmit.model_validate(payload), request, user)


@router.get("/jobs/{jid}", response_model=JobView)
def job(jid: str, request: Request, user=Depends(session)):
    return state(request).store.job(user["id"], jid)


@router.get("/media/{rid}")
def media(rid: str, request: Request, download: bool = False, user=Depends(session)):
    s = state(request)
    item = s.store.resource(user["id"], rid)
    rel = item.get("path") or item.get("saved_path")
    if not rel:
        raise HTTPException(404, "Media not found.")
    root = s.settings.data_dir_path().resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404, "Media not found.")
    if download:
        s.store.event(user["id"], "download", {"resource_id": rid})
    return FileResponse(
        path,
        filename=path.name if download else None,
        content_disposition_type="attachment" if download else "inline",
    )


@router.post("/feedback", status_code=201)
def feedback(body: Feedback, request: Request, user=Depends(session)) -> dict:
    s = state(request)
    s.store.resource(user["id"], str(body.storyboard_id), "storyboard")
    s.store.reserve(user["id"], "feedback", 20, s.settings.global_generation_limit * 20)
    s.store.event(user["id"], "feedback", body.model_dump(mode="json"))
    return {"saved": True}
