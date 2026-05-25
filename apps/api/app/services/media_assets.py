"""Resolve source media for a storyboard render.

The storyboard only carries `source_structure_card_ids`. Each StructureCard
JSON on disk carries the `source_video_job_id` it was distilled from. From
that job_id we can locate the original upload and the extracted frames.

This module does NOT modify the storyboard schema. It produces a sidecar
`MediaAssets` bundle that the renderer can merge into its inputProps.

Design notes:
    - We use absolute filesystem paths (as file:// URLs) for the renderer
      because Chromium runs headless with `disableWebSecurity: true`.
    - We also emit /static/ URLs for the frontend / debugging.
    - If nothing is found we return an empty bundle; the renderer falls
      back to the existing premium placeholder visuals.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class MediaAssets:
    """Per-storyboard media bundle passed into the Remotion renderer.

    Path semantics:
        - `*_relative_path` fields are relative to DATA_DIR and are what the
          renderer actually consumes (it mounts DATA_DIR as Remotion's
          `publicDir` and resolves them via `staticFile()`).
        - `*_path` are absolute paths -- useful for logs / debugging.
        - `*_static_url` are `/static/...` URLs for frontend / API clients.
    """

    job_id: Optional[str] = None
    source_video_path: Optional[str] = None
    source_video_relative_path: Optional[str] = None
    source_video_static_url: Optional[str] = None
    representative_frame_paths: List[str] = field(default_factory=list)
    representative_frame_relative_paths: List[str] = field(default_factory=list)
    representative_frame_static_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def has_media(self) -> bool:
        return bool(self.source_video_path) or bool(self.representative_frame_paths)


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_uuid(value: str) -> bool:
    if not value:
        return False
    if not _UUID_RE.match(value):
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def _read_card_id_to_job(data_dir: Path) -> dict[str, str]:
    """Walk `data/knowledge_base/<job_id>/structure_card.json` and build
    a map `card.id -> job_id` so we can resolve storyboard references.
    """
    kb = data_dir / "knowledge_base"
    mapping: dict[str, str] = {}
    if not kb.is_dir():
        return mapping

    for sub in kb.iterdir():
        if not sub.is_dir() or not _is_uuid(sub.name):
            continue
        card_path = sub / "structure_card.json"
        if not card_path.is_file():
            continue
        try:
            blob = json.loads(card_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Skipping unreadable structure card at %s: %s", card_path, exc)
            continue
        card_id = blob.get("id")
        source_job = blob.get("source_video_job_id")
        if isinstance(card_id, str) and isinstance(source_job, str) and source_job:
            mapping[card_id] = source_job
    return mapping


def _find_uploaded_video(data_dir: Path, job_id: str) -> Optional[Path]:
    """Return the path to the uploaded original.* file, if it exists."""
    upload_dir = data_dir / "uploads" / job_id
    if not upload_dir.is_dir():
        return None
    # Prefer `original.*`; otherwise fall back to the first video-like file.
    candidates: list[Path] = []
    for p in upload_dir.iterdir():
        if not p.is_file():
            continue
        if p.stem.lower() == "original":
            return p
        candidates.append(p)
    candidates.sort(key=lambda p: p.name)
    return candidates[0] if candidates else None


def _find_extracted_frames(data_dir: Path, job_id: str) -> List[Path]:
    """Return sorted absolute paths to `frame_*.jpg` for a job_id."""
    frames_dir = data_dir / "frames" / job_id
    if not frames_dir.is_dir():
        return []
    frames = sorted(
        p for p in frames_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        and p.stem.lower().startswith("frame_")
    )
    return frames


def _resolve_job_id_for_storyboard(
    *,
    data_dir: Path,
    storyboard: dict,
) -> Optional[str]:
    """Pick the first usable job_id referenced by the storyboard.

    Strategy:
        1. Map every `source_structure_card_ids[*]` to a job_id by reading
           saved structure cards.
        2. Return the first job_id whose upload dir actually exists. This
           keeps things deterministic for the first card in the list.
    """
    card_ids = storyboard.get("source_structure_card_ids") or []
    if not isinstance(card_ids, list) or not card_ids:
        return None

    mapping = _read_card_id_to_job(data_dir)
    for cid in card_ids:
        if not isinstance(cid, str):
            continue
        job_id = mapping.get(cid)
        if not job_id:
            continue
        if (data_dir / "uploads" / job_id).is_dir():
            return job_id
    return None


def _relative_under_data_dir(p: Path, data_dir: Path) -> Optional[str]:
    try:
        rel = p.resolve().relative_to(data_dir.resolve())
    except ValueError:
        return None
    return rel.as_posix()


def _to_static_url(p: Path, data_dir: Path) -> Optional[str]:
    """Convert an absolute path under DATA_DIR to its /static/... URL."""
    rel = _relative_under_data_dir(p, data_dir)
    return f"/static/{rel}" if rel else None


def resolve_media_assets(
    *,
    data_dir: Path,
    storyboard: dict,
    max_frames: int = 16,
) -> MediaAssets:
    """Build a `MediaAssets` bundle for the given storyboard JSON.

    Always returns a value -- empty bundle when nothing is found.
    """
    job_id = _resolve_job_id_for_storyboard(
        data_dir=data_dir, storyboard=storyboard
    )
    if not job_id:
        return MediaAssets()

    video = _find_uploaded_video(data_dir, job_id)
    frames = _find_extracted_frames(data_dir, job_id)[:max_frames]

    assets = MediaAssets(job_id=job_id)

    if video is not None:
        assets.source_video_path = str(video.resolve())
        rel = _relative_under_data_dir(video, data_dir)
        if rel:
            assets.source_video_relative_path = rel
        static = _to_static_url(video, data_dir)
        if static is not None:
            assets.source_video_static_url = static

    if frames:
        assets.representative_frame_paths = [str(p.resolve()) for p in frames]
        rels = [_relative_under_data_dir(p, data_dir) for p in frames]
        assets.representative_frame_relative_paths = [r for r in rels if r]
        statics = [_to_static_url(p, data_dir) for p in frames]
        assets.representative_frame_static_urls = [s for s in statics if s]

    log.info(
        "Resolved media assets job_id=%s video=%s frames=%d",
        job_id,
        bool(video),
        len(frames),
    )
    return assets


__all__ = ["MediaAssets", "resolve_media_assets"]
