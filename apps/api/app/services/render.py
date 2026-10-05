"""Render service: turn a saved Storyboard JSON into an mp4 via Remotion.

The actual rendering happens in a Node subprocess running
`apps/renderer/render.mjs`, which bundles the Remotion project and calls
`renderMedia()`. We pass the storyboard JSON path + an output path; the
script writes the mp4 to disk and exits 0/non-zero.

This module only orchestrates: it does not embed any video logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import shutil
import time
import uuid
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import RENDERER_DIR
from app.schemas.render_job import RenderJob, RenderMediaSummary
from app.services.media_assets import MediaAssets, resolve_media_assets

log = logging.getLogger(__name__)

#: Hard cap on render time. A 30s 1080p vertical short typically finishes
#: in under 2 minutes on a laptop; we allow plenty of headroom.
_RENDER_TIMEOUT_SECONDS = 600

#: Path of the CLI relative to the renderer dir.
_CLI_RELATIVE = "render.mjs"


class RendererSetupError(RuntimeError):
    """Raised when the renderer cannot be located or is missing deps."""


class RenderError(RuntimeError):
    """Raised when the renderer subprocess fails."""

    def __init__(self, message: str, stderr_tail: str = "") -> None:
        super().__init__(message)
        self.stderr_tail = stderr_tail


def storyboard_json_path(data_dir: Path, storyboard_id: str) -> Path:
    return data_dir / "knowledge_base" / "storyboards" / f"{storyboard_id}.json"


def render_output_path(data_dir: Path, storyboard_id: str) -> Path:
    return data_dir / "renders" / storyboard_id / "final.mp4"


def render_output_relative(storyboard_id: str) -> str:
    """Path relative to DATA_DIR (matches the /static mount layout)."""
    return f"renders/{storyboard_id}/final.mp4"


def _resolve_node_bin() -> str:
    """Locate the Node binary. Allows override via NODE_BIN."""
    override = os.environ.get("NODE_BIN")
    if override:
        return override
    found = shutil.which("node")
    if not found:
        raise RendererSetupError(
            "`node` not found on PATH. Install Node.js >= 18 or set NODE_BIN."
        )
    return found


def _ensure_renderer_ready() -> Path:
    """Make sure the renderer dir + CLI + Remotion deps exist.

    Returns the CLI path. Workspace-hoisted node_modules at the repo root
    are accepted (Node's module resolution walks upward), so we only insist
    that `@remotion/bundler` is resolvable from somewhere on the path
    between RENDERER_DIR and the filesystem root.
    """
    if not RENDERER_DIR.is_dir():
        raise RendererSetupError(f"Renderer directory missing: {RENDERER_DIR}")
    cli = RENDERER_DIR / _CLI_RELATIVE
    if not cli.is_file():
        raise RendererSetupError(
            f"Renderer CLI missing: {cli}. Run `npm install --workspace apps/renderer`."
        )
    if not _has_remotion_bundler(RENDERER_DIR):
        raise RendererSetupError(
            "@remotion/bundler is not installed. "
            "Run `npm install --workspace apps/renderer` from the repo root."
        )
    return cli


def _has_remotion_bundler(start: Path) -> bool:
    """Walk upward looking for node_modules/@remotion/bundler/package.json."""
    cur = start.resolve()
    for _ in range(8):
        candidate = cur / "node_modules" / "@remotion" / "bundler" / "package.json"
        if candidate.is_file():
            return True
        if cur.parent == cur:
            break
        cur = cur.parent
    return False


async def _run_renderer(
    *,
    cli: Path,
    storyboard_path: Path,
    output_path: Path,
    public_dir: Optional[Path] = None,
    media_assets_path: Optional[Path] = None,
) -> tuple[int, str, str]:
    """Spawn the Node CLI and capture stdout/stderr."""
    node_bin = _resolve_node_bin()
    log.info(
        "Spawning renderer: %s %s --storyboard %s --output %s media=%s public=%s",
        node_bin,
        cli,
        storyboard_path,
        output_path,
        media_assets_path,
        public_dir,
    )

    argv: list[str] = [
        node_bin,
        str(cli),
        "--storyboard",
        str(storyboard_path),
        "--output",
        str(output_path),
    ]
    if public_dir is not None:
        argv.extend(["--public-dir", str(public_dir)])
    if media_assets_path is not None:
        argv.extend(["--media-assets", str(media_assets_path)])

    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(RENDERER_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )

    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=_RENDER_TIMEOUT_SECONDS
        )
    except asyncio.CancelledError:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await proc.wait()
        raise
    except asyncio.TimeoutError as exc:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await proc.wait()
        raise RenderError(
            f"Renderer timed out after {_RENDER_TIMEOUT_SECONDS}s"
        ) from exc

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    return proc.returncode or 0, stdout, stderr


def _stderr_tail(text: str, max_lines: int = 30) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:])


async def render_storyboard(
    *,
    storyboard_id: str,
    data_dir: Path,
    snapshot: dict | None = None,
    render_id: str | None = None,
    generated_clips: dict | None = None,
    audio_path: str | None = None,
) -> RenderJob:
    """Render an immutable snapshot using only this job's staged assets."""
    sb_path = storyboard_json_path(data_dir, storyboard_id)
    sb_json = snapshot or json.loads(sb_path.read_text(encoding="utf-8"))
    if not sb_json.get("scenes"):
        raise ValueError("The storyboard has no scenes.")
    cli = _ensure_renderer_ready()
    rj_id = render_id or str(uuid.uuid4())
    relative = f"renders/{storyboard_id}/{rj_id}/final.mp4"
    output_path = data_dir / relative
    output_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_path.parent / "storyboard.json"
    snapshot_path.write_text(json.dumps(sb_json), encoding="utf-8")
    media = resolve_media_assets(data_dir=data_dir, storyboard=sb_json)
    if sb_json.get("target_media_job_id") and not media.has_media:
        raise ValueError("Target media is missing. Upload it again.")
    started, created = time.monotonic(), datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="viralcraft-render-") as tmp:
        stage = Path(tmp)

        def copy_asset(relative_path: str, name: str) -> str:
            source = (data_dir / relative_path).resolve()
            if not source.is_relative_to(data_dir.resolve()) or not source.is_file():
                raise ValueError("Render asset is unavailable.")
            dest = stage / (name + source.suffix)
            shutil.copy2(source, dest)
            return dest.name

        bundle = {"job_id": media.job_id, "representative_frame_relative_paths": []}
        if media.source_video_relative_path:
            bundle["source_video_relative_path"] = copy_asset(
                media.source_video_relative_path, "source"
            )
            from app.services.video_analysis import _read_metadata

            bundle["source_duration_seconds"] = _read_metadata(
                data_dir / media.source_video_relative_path
            ).duration_seconds
        for i, rel in enumerate(media.representative_frame_relative_paths):
            bundle["representative_frame_relative_paths"].append(
                copy_asset(rel, f"frame_{i}")
            )
        bundle["scene_clips"] = {}
        for i, (scene_id, clip) in enumerate((generated_clips or {}).items()):
            bundle["scene_clips"][scene_id] = {
                "path": copy_asset(clip["path"], f"generated_{i}"),
                "duration_seconds": clip["duration_seconds"],
            }
        if audio_path:
            bundle["audio_relative_path"] = copy_asset(audio_path, "audio")
        sidecar = output_path.parent / "media_assets.json"
        sidecar.write_text(json.dumps(bundle), encoding="utf-8")
        rc, stdout, stderr = await _run_renderer(
            cli=cli,
            storyboard_path=snapshot_path,
            output_path=output_path,
            public_dir=stage,
            media_assets_path=sidecar,
        )
    shutil.rmtree(output_path.parent / "bundle", ignore_errors=True)
    if rc != 0 or not output_path.exists():
        log.error("Render failed: %s", _stderr_tail(stderr))
        raise RenderError(
            "Render failed. Please retry.", stderr_tail=_stderr_tail(stderr)
        )
    return RenderJob(
        render_job_id=rj_id,
        storyboard_id=storyboard_id,
        status="succeeded",
        output_path=relative,
        output_url=f"/api/media/{rj_id}",
        duration_ms=int((time.monotonic() - started) * 1000),
        media_summary=_summarize_media(media),
        created_at=created,
    )


def _summarize_media(assets: MediaAssets) -> RenderMediaSummary:
    """Reduce a `MediaAssets` bundle to the compact summary surfaced on
    the RenderJob (so the UI can show what footage was reused)."""
    used_video = bool(assets.source_video_relative_path)
    frame_count = len(assets.representative_frame_relative_paths)
    return RenderMediaSummary(
        used_source_video=used_video,
        used_frames=frame_count > 0,
        frame_count=frame_count,
        source_job_id=assets.job_id,
        placeholder_only=not assets.has_media,
    )


__all__ = [
    "RenderError",
    "RendererSetupError",
    "render_output_path",
    "render_output_relative",
    "render_storyboard",
    "storyboard_json_path",
]
