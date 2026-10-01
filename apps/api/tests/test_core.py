import asyncio
import copy
import tempfile
import unittest
import uuid
from pathlib import Path
from app.runtime.store import Store, StoreError
from app.schemas.storyboard import StoryboardEdit
from app.schemas.structure_card import StructureCard
from app.services.storyboard import generate_storyboard
from app.services.editor import edit_storyboard
from app.services.media_assets import resolve_media_assets
from app.llm.mock_client import MockClient


def make_card():
    return StructureCard(
        id=str(uuid.uuid4()),
        pattern_name="Hook reveal",
        summary="A reference pattern",
        hook_type="question",
        narrative_flow="hook then reveal",
        visual_style="clean",
        editing_atoms=[
            {"kind": "hook", "duration_seconds": 5},
            {"kind": "reveal", "duration_seconds": 5},
            {"kind": "payoff", "duration_seconds": 5},
        ],
        reusable_rules=[],
        source_video_job_id=str(uuid.uuid4()),
        source_segments=[],
        created_at="2026-09-29T00:00:00Z",
    )


def make_board():
    return asyncio.run(
        generate_storyboard(
            user_prompt="A coffee shop. Visit us.",
            target_duration_seconds=15,
            cards=[make_card()],
            llm_client=MockClient(),
            target_media_job_id=str(uuid.uuid4()),
        )
    )


class CoreTests(unittest.TestCase):
    def test_target_media_never_falls_back_to_reference(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            board = make_board()
            target = root / "uploads" / board.target_media_job_id
            target.mkdir(parents=True)
            (target / "original.mp4").write_bytes(b"target")
            self.assertEqual(
                resolve_media_assets(
                    data_dir=root, storyboard=board.model_dump()
                ).job_id,
                board.target_media_job_id,
            )
            (target / "original.mp4").unlink()
            target.rmdir()
            with self.assertRaises(ValueError):
                resolve_media_assets(data_dir=root, storyboard=board.model_dump())

    def test_edit_preserves_timing_and_lineage(self):
        b = make_board()
        scenes = copy.deepcopy(b.scenes)
        scenes[0].duration_seconds = 3
        scenes[0].text = "Fresh coffee"
        scenes[0].source_structure_card_id = "forged"
        edited = edit_storyboard(
            b, StoryboardEdit(version=1, title=b.title, scenes=scenes)
        )
        self.assertEqual(edited.version, 2)
        self.assertEqual(edited.actual_duration_seconds, 13)
        self.assertEqual(edited.scenes[1].start_time, 3)
        self.assertEqual(
            edited.scenes[0].source_structure_card_id,
            b.scenes[0].source_structure_card_id,
        )
        with self.assertRaises(ValueError):
            edit_storyboard(
                edited, StoryboardEdit(version=1, title=b.title, scenes=scenes)
            )

    def test_ownership_quota_dedupe_recovery(self):
        with tempfile.TemporaryDirectory() as t:
            s = Store(Path(t))
            token, a = s.redeem(s.create_invite(1), 7)
            _, b = s.redeem(s.create_invite(1), 7)
            self.assertEqual(s.session(token)["id"], a)
            s.put_resource(a, "storyboard", {"id": "draft", "version": 1})
            with self.assertRaises(StoreError):
                s.resource(b, "draft")
            j = s.enqueue(a, "generate", {"prompt": "one"}, 1, 1, 2)
            self.assertEqual(
                j["id"], s.enqueue(a, "generate", {"prompt": "one"}, 1, 1, 2)["id"]
            )
            with self.assertRaises(StoreError):
                s.enqueue(a, "generate", {"prompt": "two"}, 1, 1, 2)
            self.assertEqual(s.claim()["id"], j["id"])
            s.recover()
            self.assertEqual(s.job(a, j["id"])["status"], "failed")
            with self.assertRaises(StoreError):
                s.job(b, j["id"])

    def test_parallel_quota_is_atomic(self):
        from concurrent.futures import ThreadPoolExecutor

        with tempfile.TemporaryDirectory() as t:
            store = Store(Path(t))

            def reserve(i):
                try:
                    store.reserve(str(i), "video", 2, 2)
                    return True
                except StoreError:
                    return False

            with ThreadPoolExecutor(max_workers=8) as pool:
                self.assertEqual(sum(pool.map(reserve, range(12))), 2)
            self.assertEqual(store.usage("__global__")["video"], 2)

    def test_retry_ownership_and_snapshot_version(self):
        with tempfile.TemporaryDirectory() as t:
            store = Store(Path(t))
            j = store.enqueue(
                "a",
                "render",
                {
                    "kind": "render",
                    "resource_id": "x",
                    "version": 1,
                    "snapshot": {"version": 1},
                },
                3,
                10,
                2,
            )
            with self.assertRaises(StoreError):
                store.retry_payload("a", j["id"])
            store.finish(j["id"], "a", error="timeout")
            with self.assertRaises(StoreError):
                store.retry_payload("b", j["id"])
            self.assertNotIn("snapshot", store.retry_payload("a", j["id"]))
            self.assertEqual(store.retry_payload("a", j["id"])["version"], 1)
