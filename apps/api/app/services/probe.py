import asyncio
import json
import os
import shutil
from pathlib import Path


async def probe_media(path: Path) -> dict:
    binary = shutil.which("ffprobe")
    if not binary:
        from app.core.config import REPO_ROOT

        options = list(
            (REPO_ROOT / "node_modules/@remotion").glob("compositor-*/ffprobe*")
        )
        if options:
            binary = str(options[0])
    if not binary:
        raise ValueError("Install FFmpeg to validate audio files.")
    p = await asyncio.create_subprocess_exec(
        binary,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "DYLD_LIBRARY_PATH": str(Path(binary).parent)},
    )
    try:
        out, _ = await asyncio.wait_for(p.communicate(), 20)
    except asyncio.TimeoutError:
        p.kill()
        await p.wait()
        raise ValueError("Media validation timed out.")
    if p.returncode:
        raise ValueError("Media cannot be decoded.")
    return json.loads(out)
