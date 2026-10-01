"""Optional scene assets. Persist provider IDs before polling; never retry POST blindly."""

from __future__ import annotations
import asyncio
import base64
import hashlib
import json
import re
import shutil
import time
import uuid
from urllib.parse import urlparse
import httpx
from app.core.errors import public_error
from app.schemas.storyboard import Storyboard
from app.services.storyboard import persist_storyboard
from app.services.video_analysis import _read_metadata


class VideoSubmissionRejected(ValueError):
    """A definitive 4xx rejection, distinct from an uncertain POST outcome."""

    def __init__(self, status_code, provider_code):
        self.status_code = status_code
        self.provider_code = provider_code
        super().__init__(
            f"Video request rejected: HTTP {status_code}, {provider_code}."
        )


class SeedanceClient:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.http = httpx.AsyncClient(timeout=40, transport=transport)
        self.root = (
            settings.seedance_api_base_url.rstrip("/") + "/contents/generations/tasks"
        )
        self.headers = {"Authorization": f"Bearer {settings.seedance_api_key}"}

    async def submit(self, prompt, reference=None):
        content = [{"type": "text", "text": prompt}]
        if reference:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": reference},
                    "role": "reference_image",
                }
            )
        body = {
            "model": self.settings.seedance_model,
            "content": content,
            "duration": 5,
            "resolution": "720p",
            "ratio": "9:16",
            "generate_audio": False,
        }
        if reference:
            body["omni_reference_task_type"] = "reference"
        r = await self.http.post(self.root, headers=self.headers, json=body)
        if r.status_code in (400, 401, 403, 404, 422):
            try:
                code = str(r.json().get("error", {}).get("code", "RequestRejected"))
            except (ValueError, AttributeError):
                code = "RequestRejected"
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", code):
                code = "RequestRejected"
            raise VideoSubmissionRejected(r.status_code, code)
        r.raise_for_status()
        return r.json()["id"]

    async def get(self, rid):
        r = await self.http.get(self.root + "/" + rid, headers=self.headers)
        r.raise_for_status()
        return r.json()

    async def close(self):
        await self.http.aclose()


class MockVisualClient:
    """Explicitly simulated status path for offline tests; does not synthesize video."""

    async def submit(self, prompt, reference=None):
        return "mock-" + str(uuid.uuid4())

    async def get(self, rid):
        return {"id": rid, "status": "succeeded", "mock": True, "usage": {}}

    async def close(self):
        pass


async def download_video(client, url, out):
    parsed = urlparse(url)
    # URLs come only from the configured provider, never from the user or LLM.
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError("Invalid provider media URL.")
    import socket, ipaddress

    addresses = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, 443)
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise ValueError("Invalid provider media host.")
    total = 0
    temp = out.with_suffix(".part")
    try:
        async with client.stream("GET", url, follow_redirects=False) as r:
            r.raise_for_status()
            if r.status_code != 200:
                raise ValueError("Provider download did not return a file.")
            with temp.open("wb") as f:
                async for chunk in r.aiter_bytes():
                    total += len(chunk)
                    if total > 50 * 1024 * 1024:
                        raise ValueError("Generated clip exceeds the file size limit.")
                    f.write(chunk)
        temp.replace(out)
    finally:
        temp.unlink(missing_ok=True)


async def generate_assets(settings, store, owner, payload, client=None):
    board = Storyboard.model_validate(payload["snapshot"])
    d = settings.data_dir_path()
    own = client is None
    client = client or (
        MockVisualClient()
        if settings.seedance_provider == "mock"
        else SeedanceClient(settings)
    )
    if (
        own
        and settings.seedance_provider != "mock"
        and (not settings.seedance_api_key or not settings.seedance_model)
    ):
        await client.close()
        raise ValueError("Video provider configuration is incomplete.")
    reference = None
    reference_hash = None
    if payload.get("reference_frame_id"):
        frame = store.resource(owner, payload["reference_frame_id"], "frame")
        raw = (d / frame["path"]).read_bytes()
        reference_hash = hashlib.sha256(raw).hexdigest()
        reference = "data:image/jpeg;base64," + base64.b64encode(raw).decode()
    warnings = []
    attached = {}
    try:
        for scene in board.scenes:
            if scene.scene_id not in payload["scene_ids"]:
                continue
            prompt = scene.asset_prompt or scene.visual_description
            key = hashlib.sha256(
                json.dumps(
                    [
                        owner,
                        settings.seedance_provider,
                        settings.seedance_model,
                        prompt,
                        reference_hash,
                        5,
                        "720p",
                        "9:16",
                    ]
                ).encode()
            ).hexdigest()
            task = store.provider_task(key, owner)
            try:
                if task and task.get("asset_id"):
                    asset = store.resource(owner, task["asset_id"], "asset")
                    if (d / asset["path"]).is_file():
                        attached[scene.scene_id] = asset["id"]
                        continue
                if task and task.get("status") == "submission_unknown":
                    raise ValueError(
                        "Video submission outcome is unknown. Check the provider console before retrying."
                    )
                # A new explicit assets job may retry a definitively rejected POST.
                # Unknown submissions and known provider IDs never reach this branch.
                if not task or task.get("status") in ("rejected", "confirmed_absent"):
                    store.reserve(owner, "video", 2, settings.seedance_global_limit)
                    task = {
                        "status": "submission_unknown",
                        "model": settings.seedance_model,
                        "prompt": prompt,
                        "reference_hash": reference_hash,
                        "created_at": time.time(),
                    }
                    store.save_provider_task(key, owner, task)
                    request_id = await client.submit(prompt, reference)
                    task.update(provider_request_id=request_id, status="queued")
                    store.save_provider_task(key, owner, task)
                deadline = time.monotonic() + settings.seedance_timeout_seconds
                while True:
                    if time.monotonic() > deadline:
                        raise TimeoutError(
                            "Video generation timed out; its request ID is saved."
                        )
                    try:
                        result = await client.get(task["provider_request_id"])
                    except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                        if isinstance(
                            exc, httpx.HTTPStatusError
                        ) and exc.response.status_code not in (429, 500, 502, 503, 504):
                            raise
                        await asyncio.sleep(settings.seedance_poll_seconds)
                        continue
                    task.update(status=result["status"], usage=result.get("usage", {}))
                    store.save_provider_task(key, owner, task)
                    if result["status"] == "succeeded":
                        break
                    if result["status"] in ("failed", "cancelled", "expired"):
                        raise ValueError(
                            "Video generation failed. Original footage is still available."
                        )
                    await asyncio.sleep(settings.seedance_poll_seconds)
                aid = str(uuid.uuid4())
                folder = d / "generated_assets" / board.id
                folder.mkdir(parents=True, exist_ok=True)
                out = folder / (aid + ".mp4")
                if result.get("mock"):
                    source = store.resource(owner, board.target_media_job_id, "upload")
                    shutil.copy2(d / source["saved_path"], out)
                else:
                    async with httpx.AsyncClient(timeout=60) as downloader:
                        await download_video(
                            downloader, result["content"]["video_url"], out
                        )
                meta = await asyncio.to_thread(_read_metadata, out)
                if meta.duration_seconds > 35:
                    raise ValueError("Unexpected generated clip duration.")
                asset = {
                    "id": aid,
                    "path": out.relative_to(d).as_posix(),
                    "duration_seconds": meta.duration_seconds,
                    "provider_request_id": task["provider_request_id"],
                    "model": settings.seedance_model,
                    "prompt": prompt,
                    "reference_hash": reference_hash,
                    "usage": result.get("usage", {}),
                    "mock": bool(result.get("mock")),
                }
                store.put_resource(owner, "asset", asset)
                out.with_suffix(".json").write_text(json.dumps(asset, indent=2))
                task.update(asset_id=aid)
                store.save_provider_task(key, owner, task)
                attached[scene.scene_id] = aid
                store.event(
                    owner,
                    "video_usage",
                    {
                        "model": settings.seedance_model,
                        "usage": asset["usage"],
                        "mock": asset["mock"],
                    },
                )
            except Exception as exc:
                if task:
                    task["last_error"] = {"type": type(exc).__name__}
                    if isinstance(exc, VideoSubmissionRejected):
                        task.update(status="rejected")
                        task["last_error"].update(
                            http_status=exc.status_code, provider_code=exc.provider_code
                        )
                    elif isinstance(exc, httpx.HTTPStatusError):
                        task["last_error"]["http_status"] = exc.response.status_code
                    store.save_provider_task(key, owner, task)
                warnings.append(f"{scene.scene_id}: {public_error(exc)}")
        if attached:
            current = store.resource(owner, board.id, "storyboard")
            if current["version"] != board.version:
                warnings.append(
                    "Draft changed while clips were generating. Clips are saved; regenerate from the latest saved draft to attach them."
                )
            else:
                scenes = [
                    (
                        s.model_copy(
                            update={
                                "asset_strategy": "generated_video",
                                "generated_asset_id": attached[s.scene_id],
                            }
                        )
                        if s.scene_id in attached
                        else s
                    )
                    for s in board.scenes
                ]
                board = board.model_copy(
                    update={"scenes": scenes, "version": board.version + 1}
                )
                store.put_resource(
                    owner,
                    "storyboard",
                    board.model_dump(mode="json"),
                    expected_version=board.version - 1,
                )
                persist_storyboard(d, board)
        return {
            "storyboard_id": board.id,
            "version": board.version,
            "attached": attached,
            "warnings": "; ".join(warnings),
        }
    finally:
        if own:
            await client.close()
