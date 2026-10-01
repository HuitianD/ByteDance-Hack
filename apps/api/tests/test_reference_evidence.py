"""Offline contracts for grounded reference extraction; no model or network calls."""

import base64
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import cv2
import httpx
import numpy as np

from app.llm.base import LLMClient, LLMError, LLMImage
from app.llm.seed_client import SeedClient
from app.schemas.structure_card import StructureCard
from app.schemas.video import FrameInfo, SceneSegment, VideoAnalysis
from app.services.structure_card import (
    StructureCardValidationError,
    build_extract_prompt,
    build_mock_structure_card_data,
    extract_structure_card,
)


def analysis_fixture(root: Path, count=3, large=False):
    directory = root / "frames" / "source-a"
    directory.mkdir(parents=True)
    frames = []
    for index in range(count):
        path = directory / f"frame_{index:03d}.jpg"
        size = (1000, 1700, 3) if large and index == 0 else (64, 96, 3)
        image = np.zeros(size, dtype=np.uint8)
        image[:, :, index % 3] = 180
        assert cv2.imwrite(str(path), image)
        frames.append(
            FrameInfo(
                index=index,
                timestamp_seconds=index * 6 / count,
                path=path.relative_to(root).as_posix(),
            )
        )
    return VideoAnalysis(
        id="analysis-a",
        job_id="source-a",
        source_video_path="private-expected-pattern.mp4",
        duration_seconds=6,
        fps=30,
        width=96,
        height=64,
        total_frames=180,
        file_size_bytes=1234,
        frames=frames,
        scenes=[
            SceneSegment(
                id=f"scene-{i}",
                start_seconds=i * 2,
                end_seconds=i * 2 + 2,
                role="SECRET EXPECTED ANSWER",
            )
            for i in range(3)
        ],
        scene_detection_method="time_based",
        created_at=datetime.now(timezone.utc),
    )


def grounded_response(analysis):
    raw = build_mock_structure_card_data(analysis)
    raw.update(
        observations=[
            dict(
                id="obs-1",
                aspect="hook",
                start_seconds=0,
                end_seconds=2,
                frame_indices=[0],
                source_segments=["scene-0"],
                observation="The first sampled frame has a blue field.",
            )
        ],
        rules=[
            dict(
                id="rule-1",
                instruction="Open with a contrasting product close-up.",
                evidence_ids=["obs-1"],
            )
        ],
        applicability=["Short product introductions"],
        material_requirements=["A close-up of the user's product"],
        id="forged-id",
        origin="human_verified",
        version=20,
        schema_version=99,
        review=dict(status="approved", method="human", reviewer="fake"),
        evidence_frames=[
            dict(index=999, timestamp_seconds=300, url="https://example.com/fake")
        ],
        analysis=dict(
            mode="vision", model="fake", frame_count=999, prompt_version="fake"
        ),
        source=dict(kind="licensed_reference", title="Fake provenance"),
    )
    return raw


class FakeClient(LLMClient):
    provider_name = "fake"

    def __init__(self, response):
        self.response = response
        self.images = None
        self.prompt = None
        self.text_calls = 0

    async def generate_text(self, prompt, **kwargs):
        raise AssertionError("Unexpected text completion")

    async def generate_json(self, prompt, **kwargs):
        self.text_calls += 1
        self.prompt = prompt
        return copy.deepcopy(self.response)

    async def generate_json_with_images(self, prompt, *, images, **kwargs):
        self.images = images
        self.prompt = prompt
        return copy.deepcopy(self.response)


class TextOnlyClient(FakeClient):
    generate_json_with_images = LLMClient.generate_json_with_images


class ReferenceEvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_frame_scene_ids_assign_exact_cut_to_next_scene(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analysis = analysis_fixture(root)
            prompt = build_extract_prompt(analysis, frames=analysis.frames, visual=True)
            metadata = json.JSONDecoder().raw_decode(
                prompt.split("## Video Analysis\n", 1)[1].lstrip()
            )[0]
            self.assertEqual(metadata["frames"][0]["scene_ids"], ["scene-0"])
            self.assertEqual(metadata["frames"][1]["scene_ids"], ["scene-1"])
            self.assertEqual(metadata["frames"][2]["scene_ids"], ["scene-2"])
            self.assertIn("half-open", prompt)
            response = grounded_response(analysis)
            response["observations"][0].update(frame_indices=[1])
            # A frame at t=2 must not be accepted in scene-0 [0, 2), even
            # though it is on the inclusive observation endpoint.
            with self.assertRaisesRegex(
                StructureCardValidationError, "cited source scenes"
            ):
                await extract_structure_card(
                    analysis, FakeClient(response), data_dir=root
                )

    async def test_observation_timestamp_rounding_tolerance_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analysis = analysis_fixture(root)
            analysis.frames[1].timestamp_seconds = 2.5
            cases = [
                (2.4999995, 3.0, True),
                (2.5000005, 3.0, True),
                (2.0, 2.4999995, True),
                (2.502, 3.0, False),
                (2.0, 2.498, False),
            ]
            for start, end, accepted in cases:
                with self.subTest(start=start, end=end):
                    response = grounded_response(analysis)
                    response["observations"][0].update(
                        start_seconds=start,
                        end_seconds=end,
                        frame_indices=[1],
                        source_segments=["scene-1"],
                    )
                    call = extract_structure_card(
                        analysis, FakeClient(response), data_dir=root
                    )
                    if accepted:
                        card = await call
                        self.assertEqual(card.evidence_frames[1].timestamp_seconds, 2.5)
                    else:
                        with self.assertRaisesRegex(
                            StructureCardValidationError, "outside the observation"
                        ):
                            await call

    async def test_real_jpegs_and_neutral_metadata_reach_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analysis = analysis_fixture(root, count=20, large=True)
            provider = FakeClient(grounded_response(analysis))
            card = await extract_structure_card(
                analysis, provider, data_dir=root, model_name="test-vision"
            )
            self.assertEqual(len(provider.images), 12)
            self.assertEqual(provider.text_calls, 0)
            self.assertNotIn(analysis.source_video_path, provider.prompt)
            self.assertNotIn("SECRET EXPECTED ANSWER", provider.prompt)
            self.assertNotIn("frames/source-a", provider.prompt)
            decoded = cv2.imdecode(
                np.frombuffer(
                    base64.b64decode(provider.images[0].data_url.split(",", 1)[1]),
                    np.uint8,
                ),
                cv2.IMREAD_COLOR,
            )
            self.assertEqual(max(decoded.shape[:2]), 960)
            self.assertNotEqual(card.id, "forged-id")
            self.assertEqual(
                (card.origin, card.schema_version, card.version), ("vision_llm", 2, 1)
            )
            self.assertEqual(card.review.status, "pending")
            self.assertEqual(card.review.method, "none")
            self.assertIsNone(card.review.reviewer)
            self.assertIsNone(card.source)
            self.assertEqual(card.analysis.model, "test-vision")
            self.assertEqual(card.analysis.frame_count, 12)
            self.assertEqual(card.evidence_frames[0].index, 0)
            self.assertEqual(card.evidence_frames[0].timestamp_seconds, 0)
            self.assertIsNone(card.evidence_frames[0].url)
            self.assertEqual(card.reusable_rules, [card.rules[0].instruction])
            self.assertEqual(card.source_segments, ["scene-0"])
            self.assertTrue(any("Audio" in item for item in card.limitations))

    async def test_legacy_metadata_and_mock_cannot_forge_visual_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analysis = analysis_fixture(root)
            provider = FakeClient(grounded_response(analysis))
            card = await extract_structure_card(analysis, provider)
            self.assertEqual(card.origin, "metadata_llm")
            self.assertEqual(card.schema_version, 1)
            self.assertEqual(card.analysis.mode, "metadata")
            self.assertEqual(card.observations, [])
            self.assertEqual(card.rules, [])
            self.assertEqual(card.evidence_frames, [])
            self.assertEqual(card.review.status, "pending")
            self.assertEqual(provider.text_calls, 1)
            self.assertIsNone(provider.images)
            provider.provider_name = "mock"
            mock = await extract_structure_card(analysis, provider, data_dir=root)
            self.assertEqual(mock.origin, "mock")
            self.assertEqual(mock.analysis.mode, "mock")
            self.assertEqual(mock.evidence_frames, [])
            self.assertEqual(provider.text_calls, 1)

    async def test_provider_without_vision_support_fails_without_text_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analysis = analysis_fixture(root)
            provider = TextOnlyClient(grounded_response(analysis))
            with self.assertRaisesRegex(LLMError, "does not support image"):
                await extract_structure_card(analysis, provider, data_dir=root)
            self.assertEqual(provider.text_calls, 0)

    async def test_unknown_and_inconsistent_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analysis = analysis_fixture(root)
            mutations = [
                lambda r: r["observations"][0].update(frame_indices=[999]),
                lambda r: r["observations"][0].update(source_segments=["missing"]),
                lambda r: r["source_segments"].append("missing"),
                lambda r: r["observations"][0].update(end_seconds=7),
                lambda r: r["observations"][0].update(end_seconds=6),
                lambda r: r["observations"][0].update(start_seconds=1),
                lambda r: r["observations"][0].update(end_seconds=float("inf")),
                lambda r: r["observations"][0].update(source_segments=["scene-2"]),
                lambda r: r["rules"][0].update(evidence_ids=["invented"]),
                lambda r: r["rules"].append(copy.deepcopy(r["rules"][0])),
                lambda r: r["observations"].append(copy.deepcopy(r["observations"][0])),
                lambda r: r.update(observations=[], rules=[]),
            ]
            for index, mutate in enumerate(mutations):
                with self.subTest(case=index):
                    response = grounded_response(analysis)
                    mutate(response)
                    with self.assertRaises(StructureCardValidationError):
                        await extract_structure_card(
                            analysis, FakeClient(response), data_dir=root
                        )

    async def test_cross_upload_absolute_and_symlink_frames_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analysis = analysis_fixture(root)
            other = root / "frames" / "source-b"
            other.mkdir()
            other_image = other / "frame.jpg"
            other_image.write_bytes((root / analysis.frames[0].path).read_bytes())
            link = root / "frames" / "source-a" / "alias.jpg"
            link.symlink_to(other_image)
            paths = [
                "frames/source-b/frame.jpg",
                str(other_image),
                "frames/source-a/../source-b/frame.jpg",
                "frames/source-a/alias.jpg",
            ]
            for path in paths:
                with self.subTest(path=path):
                    changed = analysis.model_copy(
                        update={
                            "frames": [
                                analysis.frames[0].model_copy(update={"path": path})
                            ]
                        }
                    )
                    provider = FakeClient(grounded_response(analysis))
                    with self.assertRaises(StructureCardValidationError):
                        await extract_structure_card(changed, provider, data_dir=root)
                    self.assertIsNone(provider.images)

    async def test_missing_corrupt_or_oversized_frames_fail_before_provider(self):
        for fixture in ("missing", "corrupt", "payload_limit"):
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                analysis = analysis_fixture(root)
                path = root / analysis.frames[0].path
                if fixture == "missing":
                    path.unlink()
                elif fixture == "corrupt":
                    path.write_bytes(b"not an image")
                provider = FakeClient(grounded_response(analysis))
                limit = 1 if fixture == "payload_limit" else 12 * 1024 * 1024
                with patch(
                    "app.services.structure_card.MAX_IMAGE_PAYLOAD_BYTES", limit
                ):
                    with self.assertRaises(StructureCardValidationError):
                        await extract_structure_card(analysis, provider, data_dir=root)
                self.assertIsNone(provider.images)

    async def test_legacy_json_defaults_to_unreviewed_version_one(self):
        with tempfile.TemporaryDirectory() as temp:
            analysis = analysis_fixture(Path(temp))
            raw = build_mock_structure_card_data(analysis)
            raw.update(
                id="old",
                source_video_job_id=analysis.job_id,
                created_at=datetime.now(timezone.utc),
            )
            card = StructureCard.model_validate(raw)
            self.assertEqual(card.schema_version, 1)
            self.assertEqual(card.version, 1)
            self.assertEqual(card.review.status, "pending")
            self.assertIsNone(card.analysis)
            self.assertEqual(card.observations, [])

    async def test_seed_sends_image_bytes_with_timestamps_and_records_usage(self):
        payloads = []

        def handle(request):
            payloads.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": '```json\n{"observed":true}\n```'}}
                    ],
                    "usage": {"prompt_tokens": 23, "completion_tokens": 5},
                },
            )

        client = SeedClient("test-key", "test-model", "test-model", thinking="disabled")
        await client.aclose()
        client._http = httpx.AsyncClient(
            base_url="https://example.test", transport=httpx.MockTransport(handle)
        )
        try:
            result = await client.generate_json_with_images(
                "Describe supplied evidence.",
                images=[
                    LLMImage(
                        index=7,
                        timestamp_seconds=3.5,
                        data_url="data:image/jpeg;base64,/9g=",
                    )
                ],
            )
            self.assertEqual(result, {"observed": True})
            payload = payloads[0]
            self.assertEqual(payload["model"], "test-model")
            self.assertEqual(payload["thinking"], {"type": "disabled"})
            content = payload["messages"][-1]["content"]
            self.assertEqual(content[2]["type"], "image_url")
            self.assertTrue(
                content[2]["image_url"]["url"].startswith("data:image/jpeg;base64,")
            )
            self.assertIn("index 7", content[1]["text"])
            self.assertIn("3.500000", content[1]["text"])
            self.assertEqual(client.last_usage["prompt_tokens"], 23)
        finally:
            await client.aclose()


if __name__ == "__main__":
    unittest.main()
