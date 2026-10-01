"""Local video sampling checks: full-clip coverage and frame-aligned evidence."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from app.services.video_analysis import _extract_frames


class FrameSamplingTests(unittest.TestCase):
    def extract(self, root: Path, frame_count: int, max_frames=12):
        fps = 10
        source = root / "fixture.mp4"
        writer = cv2.VideoWriter(
            str(source), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 64)
        )
        self.assertTrue(writer.isOpened(), "The local MP4 test codec is unavailable")
        for index in range(frame_count):
            # A different final frame proves we decoded the tail, rather than
            # merely assigning a late timestamp to an earlier image.
            color = (40, 210, 60) if index == frame_count - 1 else (190, 20, 30)
            writer.write(np.full((64, 64, 3), color, dtype=np.uint8))
        writer.release()
        frames_dir = root / "frames"
        frames_dir.mkdir()
        seeks = []
        capture_factory = cv2.VideoCapture

        class RecordingCapture:
            def __init__(self, path):
                self.capture = capture_factory(path)

            def __getattr__(self, name):
                return getattr(self.capture, name)

            def set(self, property_id, value):
                seeks.append((property_id, value))
                return self.capture.set(property_id, value)

        with patch(
            "app.services.video_analysis.cv2.VideoCapture", side_effect=RecordingCapture
        ):
            frames = _extract_frames(
                video_path=source,
                frames_dir=frames_dir,
                data_dir=root,
                duration_seconds=frame_count / fps,
                every_seconds=2,
                max_frames=max_frames,
            )
        self.assertLessEqual(len(frames), max_frames)
        self.assertEqual(len(frames), len(seeks))
        for frame, (property_id, position) in zip(frames, seeks):
            self.assertEqual(property_id, cv2.CAP_PROP_POS_FRAMES)
            self.assertEqual(frame.timestamp_seconds, position / fps)
            self.assertLess(frame.timestamp_seconds, frame_count / fps)
            self.assertTrue((root / frame.path).is_file())
        tail = cv2.imread(str(root / frames[-1].path))
        self.assertIsNotNone(tail)
        self.assertGreater(float(tail[:, :, 1].mean()), 180)
        self.assertLess(float(tail[:, :, 0].mean()), 90)
        return frames, [position for _, position in seeks]

    def test_thirty_second_video_is_uniformly_sampled_through_last_valid_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames, positions = self.extract(Path(tmp), 300)
            self.assertEqual(len(frames), 12)
            self.assertEqual(positions[0], 0)
            self.assertEqual(positions[-1], 299)
            self.assertEqual(frames[-1].timestamp_seconds, 29.9)
            steps = [b - a for a, b in zip(positions, positions[1:])]
            self.assertTrue(all(step in (27, 28) for step in steps))

    def test_short_video_keeps_two_second_cadence_and_adds_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames, positions = self.extract(Path(tmp), 150)
            self.assertEqual(positions, list(range(0, 141, 20)) + [149])
            self.assertEqual(frames[-1].timestamp_seconds, 14.9)

    def test_single_frame_clip_has_one_sample_without_seeking_eof(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames, positions = self.extract(Path(tmp), 1)
            self.assertEqual(positions, [0])
            self.assertEqual(frames[0].timestamp_seconds, 0)
