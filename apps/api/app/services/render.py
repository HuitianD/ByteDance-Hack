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
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import RENDERER_DIR
from app.schemas.render_job import RenderJob

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
) -> tuple[int, str, str]:
    """Spawn the Node CLI and capture stdout/stderr."""
    node_bin = _resolve_node_bin()
    log.info(
        "Spawning renderer: %s %s --storyboard %s --output %s",
        node_bin,
        cli,
        storyboard_path,
        output_path,
    )

    proc = await asyncio.create_subprocess_exec(
        node_bin,
        str(cli),
        "--storyboard",
        str(storyboard_path),
        "--output",
        str(output_path),
        cwd=str(RENDERER_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=_RENDER_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError as exc:
        proc.kill()
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
) -> RenderJob:
    """Run a synchronous render and return the resulting RenderJob.

    Raises:
        FileNotFoundError: storyboard JSON missing.
        RendererSetupError: node/renderer not installed.
        RenderError: subprocess failed or output file missing.
    """
    sb_path = storyboard_json_path(data_dir, storyboard_id)
    if not sb_path.exists():
        raise FileNotFoundError(
            f"No storyboard saved at {sb_path}. Generate one first via "
            "POST /storyboards/generate."
        )

    # Sanity: parse just enough to confirm it's a valid storyboard JSON.
    try:
        sb_json = json.loads(sb_path.read_text(encoding="utf-8"))
        if not isinstance(sb_json, dict) or "scenes" not in sb_json:
            raise ValueError("missing 'scenes'")
    except (json.JSONDecodeError, ValueError) as exc:
        raise RenderError(
            f"Storyboard file is not a valid storyboard: {exc}"
        ) from exc

    cli = _ensure_renderer_ready()

    output_path = render_output_path(data_dir, storyboard_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    started_at = datetime.now(timezone.utc)
    rj_id = str(uuid.uuid4())

    rc, stdout, stderr = await _run_renderer(
        cli=cli,
        storyboard_path=sb_path,
        output_path=output_path,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if rc != 0 or not output_path.exists():
        log.error("Renderer failed (rc=%s)\nSTDOUT tail:\n%s\nSTDERR tail:\n%s",
                  rc, _stderr_tail(stdout, 10), _stderr_tail(stderr, 30))
        raise RenderError(
            f"Renderer exited with code {rc}.",
            stderr_tail=_stderr_tail(stderr, 30) or _stderr_tail(stdout, 30),
        )

    if stderr.strip():
        # Remotion logs progress to stderr too; only log at debug.
        log.debug("Renderer stderr: %s", _stderr_tail(stderr, 20))

    return RenderJob(
        render_job_id=rj_id,
        storyboard_id=storyboard_id,
        status="succeeded",
        output_path=render_output_relative(storyboard_id),
        output_url=f"/static/{render_output_relative(storyboard_id)}",
        duration_ms=elapsed_ms,
        error=None,
        created_at=started_at,
    )


__all__ = [
    "RenderError",
    "RendererSetupError",
    "render_output_path",
    "render_output_relative",
    "render_storyboard",
    "storyboard_json_path",
]
