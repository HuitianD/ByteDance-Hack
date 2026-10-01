import asyncio
import tempfile
import unittest
from pathlib import Path
import httpx
from app.core.config import Settings
from app.services.visual import SeedanceClient, VideoSubmissionRejected, generate_assets
from app.services.retrieval import embed, vector_literal
from app.runtime.store import Store
from test_core import make_board


class ProviderTests(unittest.TestCase):
    def test_video_rejection_keeps_safe_code_and_explicit_retry(self):
        from unittest.mock import patch
        from types import SimpleNamespace

        b = make_board()

        async def run():
            c = SeedanceClient(
                Settings(
                    _env_file=None, seedance_model="model", seedance_api_key="secret"
                ),
                httpx.MockTransport(
                    lambda r: httpx.Response(
                        404,
                        json={
                            "error": {
                                "code": "ModelNotOpen",
                                "message": "private account information",
                            }
                        },
                    )
                ),
            )
            try:
                with self.assertRaises(VideoSubmissionRejected) as ctx:
                    await c.submit("coffee")
                self.assertEqual(ctx.exception.provider_code, "ModelNotOpen")
                self.assertNotIn("private", str(ctx.exception))
            finally:
                await c.close()

            class Provider:
                calls = 0

                async def submit(self, *args):
                    self.calls += 1
                    if self.calls == 1:
                        raise VideoSubmissionRejected(404, "ModelNotOpen")
                    return "accepted-once"

                async def get(self, rid):
                    return {"status": "succeeded", "mock": True}

            with tempfile.TemporaryDirectory() as t:
                settings = Settings(_env_file=None, data_dir=t, seedance_model="model")
                store = Store(Path(t))
                store.put_resource("a", "storyboard", b.model_dump(mode="json"))
                (Path(t) / "source.mp4").write_bytes(b"fixture")
                store.put_resource(
                    "a",
                    "upload",
                    {"id": b.target_media_job_id, "saved_path": "source.mp4"},
                )
                provider = Provider()
                payload = {
                    "snapshot": b.model_dump(mode="json"),
                    "scene_ids": [b.scenes[0].scene_id],
                }
                first = await generate_assets(settings, store, "a", payload, provider)
                self.assertIn("not activated", first["warnings"])
                with store.connection() as db:
                    import json

                    task = json.loads(
                        db.execute("SELECT body FROM provider_tasks").fetchone()[0]
                    )
                self.assertEqual(task["status"], "rejected")
                self.assertEqual(task["last_error"]["provider_code"], "ModelNotOpen")
                with patch(
                    "app.services.visual._read_metadata",
                    return_value=SimpleNamespace(duration_seconds=5),
                ):
                    second = await generate_assets(
                        settings, store, "a", payload, provider
                    )
                self.assertTrue(second["attached"])
                self.assertEqual(provider.calls, 2)

        asyncio.run(run())

    def test_planner_model_id_endpoint_override_and_thinking(self):
        from app.llm.factory import get_llm_client
        from app.core.errors import public_error

        async def run():
            settings = Settings(
                _env_file=None,
                llm_provider="seed",
                seed_api_key="fixture",
                seed_model="doubao-seed-2-1-lite-260915",
                seed_thinking="disabled",
            )
            self.assertEqual(settings.missing_for_provider(), [])
            for endpoint in (None, "ep-custom"):
                client = get_llm_client(
                    settings.model_copy(update={"seed_endpoint_id": endpoint})
                )
                seen = []
                await client._http.aclose()

                def respond(request):
                    import json

                    seen.append(json.loads(request.content))
                    return httpx.Response(
                        200,
                        json={
                            "choices": [
                                {"message": {"content": '```json\n{"ok":true}\n```'}}
                            ],
                            "usage": {"total_tokens": 12},
                        },
                    )

                client._http = httpx.AsyncClient(
                    base_url="https://example.com",
                    transport=httpx.MockTransport(respond),
                )
                try:
                    self.assertEqual(await client.generate_json("Check"), {"ok": True})
                    self.assertEqual(seen[0]["model"], endpoint or settings.seed_model)
                    self.assertEqual(seen[0]["thinking"], {"type": "disabled"})
                    self.assertEqual(client.last_usage, {"total_tokens": 12})
                finally:
                    await client.aclose()

        asyncio.run(run())
        self.assertIn("not activated", public_error(RuntimeError("ModelNotOpen")))

    def test_video_payload_and_poll_contract(self):
        requests = []

        def respond(r):
            requests.append(r)
            return httpx.Response(
                200,
                json=(
                    {"id": "task1"}
                    if r.method == "POST"
                    else {
                        "id": "task1",
                        "status": "succeeded",
                        "content": {"video_url": "https://example.com/generated.mp4"},
                    }
                ),
            )

        async def run():
            c = SeedanceClient(
                Settings(
                    _env_file=None,
                    seedance_model="configured-model",
                    seedance_api_key="private",
                ),
                httpx.MockTransport(respond),
            )
            self.assertEqual(
                await c.submit("A coffee cup", "data:image/jpeg;base64,AAA"), "task1"
            )
            self.assertEqual((await c.get("task1"))["status"], "succeeded")
            await c.close()

        asyncio.run(run())
        import json

        body = json.loads(requests[0].content)
        self.assertEqual(body["duration"], 5)
        self.assertEqual(body["resolution"], "720p")
        self.assertEqual(body["content"][1]["role"], "reference_image")
        self.assertTrue(str(requests[1].url).endswith("/tasks/task1"))

    def test_embedding_shape(self):
        async def run():
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(
                        200,
                        json={
                            "data": {"embedding": [0.1] * 1024},
                            "usage": {"total_tokens": 2},
                        },
                    )
                )
            ) as c:
                v, usage = await embed(Settings(_env_file=None), "coffee", c)
                self.assertEqual(len(v), 1024)
                self.assertEqual(usage["total_tokens"], 2)

        asyncio.run(run())
        with self.assertRaises(ValueError):
            vector_literal([1, 2])
        with self.assertRaises(ValueError):
            vector_literal([float("nan")] * 1024)

    def test_uncertain_submission_is_not_repeated(self):
        class Uncertain:
            calls = 0

            async def submit(self, *a):
                self.calls += 1
                raise httpx.ReadTimeout("timeout")

        b = make_board()

        async def run():
            with tempfile.TemporaryDirectory() as t:
                s = Settings(
                    _env_file=None,
                    data_dir=t,
                    seedance_enabled=True,
                    seedance_model="test",
                )
                store = Store(Path(t))
                store.put_resource("a", "storyboard", b.model_dump(mode="json"))
                p = {
                    "snapshot": b.model_dump(mode="json"),
                    "scene_ids": [b.scenes[0].scene_id],
                }
                c = Uncertain()
                first = await generate_assets(s, store, "a", p, c)
                second = await generate_assets(s, store, "a", p, c)
                self.assertEqual(c.calls, 1)
                self.assertTrue(first["warnings"])
                self.assertTrue(second["warnings"])
                self.assertEqual(store.resource("a", b.id)["version"], 1)

        asyncio.run(run())

    def test_completed_video_is_cached_and_failure_preserves_footage(self):
        from unittest.mock import patch
        from types import SimpleNamespace

        b = make_board()

        class Provider:
            calls = 0
            fail = False

            async def submit(self, *args):
                self.calls += 1
                return "known-task"

            async def get(self, rid):
                return {"status": "failed" if self.fail else "succeeded", "mock": True}

        async def run():
            with tempfile.TemporaryDirectory() as t:
                settings = Settings(
                    _env_file=None, data_dir=t, seedance_model="contract-test"
                )
                store = Store(Path(t))
                store.put_resource("a", "storyboard", b.model_dump(mode="json"))
                source = Path(t) / "source.mp4"
                source.write_bytes(b"fixture")
                store.put_resource(
                    "a",
                    "upload",
                    {"id": b.target_media_job_id, "saved_path": "source.mp4"},
                )
                c = Provider()
                p = {
                    "snapshot": b.model_dump(mode="json"),
                    "scene_ids": [b.scenes[0].scene_id],
                }
                with patch(
                    "app.services.visual._read_metadata",
                    return_value=SimpleNamespace(duration_seconds=5),
                ):
                    result = await generate_assets(settings, store, "a", p, c)
                    self.assertTrue(result["attached"])
                    p["snapshot"] = store.resource("a", b.id)
                    again = await generate_assets(settings, store, "a", p, c)
                    self.assertEqual(again["attached"], result["attached"])
                    self.assertEqual(c.calls, 1)
                    self.assertEqual(store.usage("__global__")["video"], 1)
                    c.fail = True
                    p["snapshot"] = store.resource("a", b.id)
                    p["scene_ids"] = [b.scenes[1].scene_id]
                    failed = await generate_assets(settings, store, "a", p, c)
                    self.assertTrue(failed["warnings"])
                    self.assertFalse(failed["attached"])
                    self.assertEqual(
                        store.resource("a", b.id)["target_media_job_id"],
                        b.target_media_job_id,
                    )

        asyncio.run(run())
