import asyncio
import unittest

from app.core.config import API_DIR, Settings
from app.llm.mock_client import MockClient
from app.schemas.video import VideoAnalysis
from app.services.structure_card import extract_structure_card
from app.services.storyboard import generate_storyboard


class BaselineTests(unittest.TestCase):
    def test_env_path_is_anchored_and_status_has_no_secrets(self):
        self.assertEqual(Settings.model_config["env_file"], API_DIR / ".env")
        s = Settings(_env_file=None, seed_api_key="never-show-this")
        self.assertNotIn("never-show-this", str(s.capabilities()))

    def test_mock_pipeline(self):
        a = VideoAnalysis(
            id="analysis",
            job_id="upload",
            source_video_path="uploads/upload/original.mp4",
            duration_seconds=15,
            fps=30,
            width=720,
            height=1280,
            total_frames=450,
            file_size_bytes=100,
            frames=[],
            scenes=[{"id": "scene_0", "start_seconds": 0, "end_seconds": 15}],
            scene_detection_method="time_based",
            created_at="2026-09-29T00:00:00Z",
        )

        async def run():
            card = await extract_structure_card(a, MockClient())
            board = await generate_storyboard(
                user_prompt="Morning coffee",
                target_duration_seconds=20,
                cards=[card],
                llm_client=MockClient(),
            )
            self.assertEqual(board.source_structure_card_ids, [card.id])
            self.assertAlmostEqual(
                sum(s.duration_seconds for s in board.scenes), 20, places=2
            )

        asyncio.run(run())
