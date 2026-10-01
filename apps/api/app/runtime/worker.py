from __future__ import annotations
import asyncio
import logging
import uuid
from app.core.config import Settings
from app.core.errors import public_error
from app.llm.factory import get_llm_client
from app.schemas.video import VideoAnalysis
from app.schemas.structure_card import StructureCard
from app.services.video_analysis import analyze_video_file
from app.services.structure_card import extract_structure_card
from app.services.storyboard import generate_storyboard, persist_storyboard
from app.services.render import render_storyboard
from app.runtime.store import Store

log = logging.getLogger(__name__)


class Worker:
    def __init__(self, settings: Settings, store: Store):
        self.settings, self.store = settings, store
        self.task = None

    async def start(self):
        self.store.recover()
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def run(self):
        while True:
            job = self.store.claim()
            if not job:
                await asyncio.sleep(0.2)
                continue
            try:
                result = await self.execute(job)
                self.store.finish(job["id"], job["owner"], result=result)
            except asyncio.CancelledError:
                self.store.finish(
                    job["id"],
                    job["owner"],
                    error="Server stopped. Saved work is available; retry this task.",
                )
                raise
            except Exception as exc:
                log.error("Job %s failed (%s)", job["id"], type(exc).__name__)
                self.store.finish(job["id"], job["owner"], error=public_error(exc))

    async def analyze(self, owner, rid):
        upload = self.store.resource(owner, rid, "upload")
        if upload.get("analysis"):
            return VideoAnalysis.model_validate(upload["analysis"])
        d = self.settings.data_dir_path()
        a = await asyncio.to_thread(
            analyze_video_file,
            job_id=rid,
            video_path=d / upload["saved_path"],
            data_dir=d,
        )
        path = d / "knowledge_base" / rid / "video_analysis.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(a.model_dump_json(indent=2))
        frames = []
        for frame in a.frames:
            fid = str(uuid.uuid4())
            self.store.put_resource(
                owner,
                "frame",
                {
                    "id": fid,
                    "path": frame.path,
                    "upload_id": rid,
                    "timestamp_seconds": frame.timestamp_seconds,
                },
            )
            frames.append(
                {
                    "id": fid,
                    "url": f"/api/media/{fid}",
                    "timestamp_seconds": frame.timestamp_seconds,
                }
            )
        upload.update(analysis=a.model_dump(mode="json"), frames=frames)
        self.store.put_resource(owner, "upload", upload)
        return a

    async def execute(self, job):
        owner, p, kind = job["owner"], job["payload"], job["kind"]
        d = self.settings.data_dir_path()
        if kind == "analyze":
            await self.analyze(owner, p["resource_id"])
            return self.store.resource(owner, p["resource_id"], "upload")
        if kind == "learn":
            a = await self.analyze(owner, p["resource_id"])
            client = get_llm_client(self.settings)
            try:
                card = await extract_structure_card(a, client)
            finally:
                self.store.event(
                    owner,
                    "planner_usage",
                    {
                        "model": self.settings.seed_model,
                        "provider": self.settings.llm_provider,
                        "usage": getattr(client, "last_usage", {}),
                    },
                )
                await client.aclose()
            path = d / "knowledge_base" / a.job_id / "structure_card.json"
            path.write_text(card.model_dump_json(indent=2))
            self.store.put_resource(owner, "card", card.model_dump(mode="json"))
            return card.model_dump(mode="json")
        if kind == "generate":
            request = p["storyboard"]
            cards = [
                StructureCard.model_validate(
                    self.store.resource(owner, c, "card", True)
                )
                for c in request["reference_card_ids"]
            ]
            target = request["target_media_job_id"]
            await self.analyze(owner, target)
            client = get_llm_client(self.settings)
            try:
                board = await generate_storyboard(
                    user_prompt=request["user_prompt"],
                    target_duration_seconds=request["target_duration_seconds"],
                    cards=cards,
                    llm_client=client,
                    target_media_job_id=target,
                )
            finally:
                self.store.event(
                    owner,
                    "planner_usage",
                    {
                        "model": self.settings.seed_model,
                        "provider": self.settings.llm_provider,
                        "usage": getattr(client, "last_usage", {}),
                    },
                )
                await client.aclose()
            persist_storyboard(d, board)
            self.store.put_resource(owner, "storyboard", board.model_dump(mode="json"))
            return board.model_dump(mode="json")
        if kind == "render":
            board = p["snapshot"]
            clips = {}
            for scene in board["scenes"]:
                if scene.get("generated_asset_id"):
                    asset = self.store.resource(
                        owner, scene["generated_asset_id"], "asset"
                    )
                    clips[scene["scene_id"]] = {
                        "path": asset["path"],
                        "duration_seconds": asset["duration_seconds"],
                    }
            audio = (
                self.store.resource(owner, board["audio_asset_id"], "audio")["path"]
                if board.get("audio_asset_id")
                else None
            )
            r = await render_storyboard(
                storyboard_id=board["id"],
                data_dir=d,
                snapshot=board,
                render_id=job["id"],
                generated_clips=clips,
                audio_path=audio,
            )
            body = r.model_dump(mode="json")
            body.update(
                id=job["id"], version=board.get("version", 1), path=r.output_path
            )
            self.store.put_resource(owner, "render", body)
            return body
        if kind == "assets":
            from app.services.visual import generate_assets

            return await generate_assets(self.settings, self.store, owner, p)
        raise ValueError("Unknown task kind.")
