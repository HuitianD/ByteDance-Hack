"""Offline acceptance of the checked-in, actually extracted reference library.

These checks validate provenance, assets and prompt plumbing; they do not
claim virality, human review, or the accuracy of every model interpretation.
No provider, database or running application is required.
"""

import hashlib
import json
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

import cv2

from app.schemas.structure_card import StructureCard
from app.schemas.video import VideoAnalysis
from app.services.storyboard import build_generate_prompt
from app.services.structure_card import _validate_visual_evidence

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "packages/reference-library"
PUBLIC = (ROOT / "apps/web/public").resolve()
REFERENCES = (PUBLIC / "references").resolve()


class BundledReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((CATALOG / "manifest.json").read_text())
        cls.entries = manifest["references"]
        cls.slugs = [entry["slug"] for entry in cls.entries]
        cls.raw = {
            slug: StructureCard.model_validate_json(
                (CATALOG / "extractions" / f"{slug}.json").read_text()
            )
            for slug in cls.slugs
        }
        cls.cards = {
            slug: StructureCard.model_validate_json(
                (CATALOG / "cards" / f"{slug}.json").read_text()
            )
            for slug in cls.slugs
        }
        cls.analyses = {
            slug: VideoAnalysis.model_validate_json(
                (CATALOG / "analyses" / f"{slug}.json").read_text()
            )
            for slug in cls.slugs
        }

    def local_reference(self, url: str) -> Path:
        parsed = urlsplit(url)
        self.assertFalse(parsed.scheme)
        self.assertFalse(parsed.netloc)
        self.assertFalse(parsed.query)
        self.assertFalse(parsed.fragment)
        path = unquote(parsed.path)
        self.assertTrue(path.startswith("/references/"), url)
        self.assertNotIn("..", Path(path).parts)
        resolved = (PUBLIC / path.lstrip("/")).resolve(strict=True)
        self.assertTrue(resolved.is_relative_to(REFERENCES), url)
        self.assertTrue(resolved.is_file(), url)
        return resolved

    def test_raw_extractions_stay_pending_and_publication_keeps_separate_identity(self):
        self.assertTrue({"showcase", "question", "list"} <= set(self.slugs))
        self.assertEqual(len(self.slugs), len(set(self.slugs)))
        self.assertEqual(
            len({card.id for card in self.cards.values()}), len(self.cards)
        )
        for slug in self.slugs:
            with self.subTest(slug=slug):
                raw, card, analysis = (
                    self.raw[slug],
                    self.cards[slug],
                    self.analyses[slug],
                )
                self.assertEqual(raw.review.status, "pending")
                self.assertEqual(raw.review.method, "none")
                self.assertIsNone(raw.review.reviewer)
                self.assertIsNone(raw.review.reviewed_at)
                self.assertEqual(raw.origin, "vision_llm")
                self.assertEqual(raw.schema_version, 2)
                self.assertEqual(raw.version, 1)
                self.assertIsNotNone(raw.analysis)
                self.assertEqual(raw.analysis.mode, "vision")
                self.assertTrue(raw.analysis.model)
                self.assertNotEqual(raw.analysis.model, "mock")
                self.assertGreater(raw.analysis.frame_count, 0)
                self.assertEqual(raw.analysis.frame_count, len(raw.evidence_frames))
                self.assertEqual(raw.source_video_job_id, analysis.job_id)
                self.assertEqual(card.source_video_job_id, raw.source_video_job_id)
                self.assertNotEqual(card.id, raw.id)
                self.assertEqual(card.review.status, "approved")
                self.assertEqual(card.review.method, "assistant_visual")
                self.assertTrue(card.review.reviewer)
                self.assertTrue(card.review.notes)
                self.assertIsNotNone(card.review.reviewed_at)
                self.assertGreater(card.version, raw.version)
                self.assertEqual(card.schema_version, raw.schema_version)
                self.assertEqual(card.origin, raw.origin)
                self.assertEqual(card.source, raw.source)
                self.assertEqual(card.evidence_frames, raw.evidence_frames)
                self.assertEqual(card.analysis, raw.analysis)
                history = StructureCard.model_validate_json(
                    (CATALOG / "reviews" / slug / f"v{card.version}.json").read_text()
                )
                self.assertEqual(history, card)
                revisions = sorted(
                    int(path.stem[1:])
                    for path in (CATALOG / "reviews" / slug).glob("v*.json")
                )
                self.assertEqual(revisions[-1], card.version)
                self.assertTrue(all(version > raw.version for version in revisions))

    def test_video_checksums_and_actual_jpeg_evidence_match_controlled_public_paths(
        self,
    ):
        for slug in self.slugs:
            with self.subTest(slug=slug):
                card, analysis = self.cards[slug], self.analyses[slug]
                self.assertIsNotNone(card.source)
                self.assertEqual(card.source.kind, "self_authored_demo")
                self.assertEqual(card.source.media_url, f"/references/{slug}.mp4")
                video = self.local_reference(card.source.media_url)
                self.assertEqual(
                    hashlib.sha256(video.read_bytes()).hexdigest(), card.source.sha256
                )
                self.assertEqual(analysis.source_video_path, card.source.media_url)
                self.assertAlmostEqual(
                    card.source.original_duration_seconds, analysis.duration_seconds
                )
                frames_by_index = {frame.index: frame for frame in analysis.frames}
                self.assertEqual(len(frames_by_index), len(analysis.frames))
                for frame in card.evidence_frames:
                    self.assertIn(frame.index, frames_by_index)
                    self.assertEqual(
                        frame.url, f"/references/{slug}/frame_{frame.index:03d}.jpg"
                    )
                    frame_path = self.local_reference(frame.url)
                    self.assertEqual(frame_path.suffix, ".jpg")
                    image = cv2.imread(str(frame_path))
                    self.assertIsNotNone(image, str(frame_path))
                    self.assertGreater(image.shape[0], 0)
                    self.assertGreater(image.shape[1], 0)
                    original = frames_by_index[frame.index]
                    self.assertEqual(original.path, frame.url)
                    self.assertAlmostEqual(
                        original.timestamp_seconds, frame.timestamp_seconds
                    )
                    self.assertLess(frame.timestamp_seconds, analysis.duration_seconds)
                for frame in analysis.frames:
                    if frame.path != "not_in_model_input":
                        self.local_reference(frame.path)

    def test_original_and_reviewed_evidence_graphs_validate_against_saved_analysis(
        self,
    ):
        for slug in self.slugs:
            for label, card in (
                ("raw", self.raw[slug]),
                ("reviewed", self.cards[slug]),
            ):
                with self.subTest(slug=slug, stage=label):
                    self.assertTrue(card.observations)
                    self.assertTrue(card.rules)
                    _validate_visual_evidence(card, self.analyses[slug])
                    self.assertEqual(
                        card.reusable_rules, [rule.instruction for rule in card.rules]
                    )
                    self.assertTrue(card.limitations)

    def test_evidence_rules_and_material_requirements_reach_storyboard_prompt(self):
        selected = list(self.cards.values())
        prompt = build_generate_prompt(
            user_prompt="为咖啡店制作一条产品介绍，只使用已有产品画面。",
            target_duration_seconds=15,
            cards=selected,
        )
        self.assertIn("## Structure Cards", prompt)
        included = json.loads(prompt.rsplit("\n## Structure Cards\n", 1)[1].strip())
        self.assertEqual(
            [item["id"] for item in included], [card.id for card in selected]
        )
        for card, item in zip(selected, included):
            with self.subTest(card_id=card.id):
                self.assertTrue(card.rules)
                self.assertTrue(card.material_requirements)
                self.assertEqual(
                    item["rules"], [rule.model_dump(mode="json") for rule in card.rules]
                )
                self.assertEqual(
                    item["material_requirements"], card.material_requirements
                )
                self.assertEqual(
                    item["observations"],
                    [obs.model_dump(mode="json") for obs in card.observations],
                )
                self.assertEqual(item["review"]["method"], "assistant_visual")


if __name__ == "__main__":
    unittest.main()
