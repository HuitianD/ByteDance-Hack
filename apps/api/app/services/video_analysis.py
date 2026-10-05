"""Basic, deterministic, non-LLM video analysis.

Pipeline:
    1. Read metadata via OpenCV.
    2. Extract representative frames across the full clip (capped).
    3. Detect scenes via PySceneDetect, with a time-based fallback.

This module is pure-ish: it reads a source video and writes JPEG frames +
returns a `VideoAnalysis`. The route layer handles persistence of the
analysis JSON to the knowledge base.
"""

from __future__ import annotations

import logging
import math
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import cv2

from app.schemas.video import FrameInfo, SceneSegment, VideoAnalysis

log = logging.getLogger(__name__)

# Tunables for the basic analyzer.
FRAME_EVERY_SECONDS: float = 2.0
MAX_FRAMES: int = 12
FALLBACK_SEGMENT_SECONDS: float = 3.0  # used when PySceneDetect is unavailable


class AnalysisError(RuntimeError):
    """Raised when the source video cannot be opened or read."""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_video_file(
    *,
    job_id: str,
    video_path: Path,
    data_dir: Path,
) -> VideoAnalysis:
    """Run basic analysis on an uploaded video file.

    Side effects:
        - Wipes and rewrites `<data_dir>/frames/<job_id>/`.
        - Writes JPEG frames into that directory.

    Args:
        job_id: Upload job_id (already validated by the caller).
        video_path: Path to the source video on disk.
        data_dir: Resolved absolute DATA_DIR.

    Returns:
        VideoAnalysis -- not yet persisted to disk; the caller decides where
        to write the JSON.
    """
    if not video_path.exists():
        raise AnalysisError(f"Source video not found: {video_path}")

    metadata = _read_metadata(video_path)
    file_size_bytes = video_path.stat().st_size

    frames_dir = data_dir / "frames" / job_id
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    frames = _extract_frames(
        video_path=video_path,
        frames_dir=frames_dir,
        data_dir=data_dir,
        duration_seconds=metadata.duration_seconds,
        every_seconds=FRAME_EVERY_SECONDS,
        max_frames=MAX_FRAMES,
    )

    scenes, method = _detect_scenes(
        video_path=video_path,
        duration_seconds=metadata.duration_seconds,
    )

    source_relative = video_path.relative_to(data_dir).as_posix()

    return VideoAnalysis(
        id=str(uuid.uuid4()),
        job_id=job_id,
        source_video_path=source_relative,
        duration_seconds=metadata.duration_seconds,
        fps=metadata.fps,
        width=metadata.width,
        height=metadata.height,
        total_frames=metadata.total_frames,
        file_size_bytes=file_size_bytes,
        frames=frames,
        scenes=scenes,
        scene_detection_method=method,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class _Metadata:
    __slots__ = ("duration_seconds", "fps", "width", "height", "total_frames")

    def __init__(
        self,
        duration_seconds: float,
        fps: float,
        width: int,
        height: int,
        total_frames: int,
    ) -> None:
        self.duration_seconds = duration_seconds
        self.fps = fps
        self.width = width
        self.height = height
        self.total_frames = total_frames


def _read_metadata(video_path: Path) -> _Metadata:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise AnalysisError(f"Could not open video: {video_path}")
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    finally:
        cap.release()

    if fps <= 0 or total_frames <= 0:
        raise AnalysisError(
            "Could not read fps/frame count from video. The file may be "
            "corrupt or in an unsupported codec."
        )

    duration_seconds = total_frames / fps
    return _Metadata(
        duration_seconds=duration_seconds,
        fps=fps,
        width=width,
        height=height,
        total_frames=total_frames,
    )


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------


def _extract_frames(
    *,
    video_path: Path,
    frames_dir: Path,
    data_dir: Path,
    duration_seconds: float,
    every_seconds: float,
    max_frames: int,
) -> List[FrameInfo]:
    if duration_seconds <= 0 or max_frames <= 0:
        return []
    if every_seconds <= 0:
        raise AnalysisError("Frame sampling interval must be positive")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise AnalysisError(f"Could not open video for frame extraction: {video_path}")

    frames: List[FrameInfo] = []
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(fps) or fps <= 0 or frame_count <= 0:
            raise AnalysisError("Could not read frame metadata for sampling")
        # Seek to frame positions, never the duration boundary (which is EOF).
        # Timestamps describe these frame-aligned seeks rather than unrounded
        # ideal intervals that may fall between actual frames.
        last_frame = min(frame_count - 1, max(0, math.ceil(duration_seconds * fps) - 1))
        regular_count = math.floor((last_frame / fps) / every_seconds) + 1
        if regular_count >= max_frames:
            count = min(max_frames, last_frame + 1)
            positions = (
                [last_frame]
                if count == 1
                else [round(i * last_frame / (count - 1)) for i in range(count)]
            )
        else:
            positions = [
                min(last_frame, round(i * every_seconds * fps))
                for i in range(regular_count)
            ]
            if positions[-1] != last_frame:
                positions.append(last_frame)
        positions = list(dict.fromkeys(positions))
        for idx, position in enumerate(positions):
            ts = position / fps
            if not cap.set(cv2.CAP_PROP_POS_FRAMES, position):
                log.warning("Failed to seek frame %d from %s", position, video_path)
                continue
            ok, frame = cap.read()
            if not ok or frame is None:
                log.warning("Failed to read frame at t=%.2fs from %s", ts, video_path)
                continue
            out_path = frames_dir / f"frame_{idx:03d}.jpg"
            ok_write = cv2.imwrite(
                str(out_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            )
            if not ok_write:
                log.warning("Failed to write frame to %s", out_path)
                continue
            frames.append(
                FrameInfo(
                    index=idx,
                    timestamp_seconds=ts,
                    path=out_path.relative_to(data_dir).as_posix(),
                )
            )
    finally:
        cap.release()

    return frames


# ---------------------------------------------------------------------------
# Scene detection (PySceneDetect with fallback)
# ---------------------------------------------------------------------------


def _detect_scenes(
    *,
    video_path: Path,
    duration_seconds: float,
) -> Tuple[List[SceneSegment], str]:
    """Try PySceneDetect; fall back to evenly-spaced time segments."""
    try:
        from scenedetect import ContentDetector, detect  # type: ignore

        raw = detect(str(video_path), ContentDetector())
        if raw:
            scenes = [
                SceneSegment(
                    id=f"scene_{i:03d}",
                    start_seconds=float(start.get_seconds()),
                    end_seconds=float(end.get_seconds()),
                )
                for i, (start, end) in enumerate(raw)
            ]
            return scenes, "pyscenedetect"
    except Exception as exc:  # noqa: BLE001 -- fall back to time-based.
        log.warning("PySceneDetect failed (%s); using time-based segmentation.", exc)

    return _time_based_scenes(duration_seconds), "time_based"


def _time_based_scenes(duration_seconds: float) -> List[SceneSegment]:
    if duration_seconds <= 0:
        return []
    segments: List[SceneSegment] = []
    t = 0.0
    i = 0
    while t < duration_seconds:
        end = min(t + FALLBACK_SEGMENT_SECONDS, duration_seconds)
        segments.append(
            SceneSegment(
                id=f"scene_{i:03d}",
                start_seconds=t,
                end_seconds=end,
            )
        )
        t = end
        i += 1
    return segments
