"""Build three self-authored reference demos offline with the existing renderer.

Run with apps/api/.venv/bin/python scripts/make_reference_demos.py.
Requires installed renderer dependencies, Chromium and the bundled source-cup.mp4.
No model or embedding APIs are called. Authoring JSON is deliberately separate
from the reference-card extraction inputs. Existing MP4 files are never replaced;
use --output-dir to build a new set while retaining previous outputs.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.schemas.storyboard import Storyboard
from app.services.probe import probe_media
from app.services.render import RenderError, render_storyboard

AUTHORING = ROOT / "packages/reference-library/authoring"
BUNDLED_MEDIA = ROOT / "apps/web/public/references"
SLUGS = ("showcase", "question", "list")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def run(args: argparse.Namespace) -> None:
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    pending = [slug for slug in args.slugs if not (output / f"{slug}.mp4").exists()]
    for slug in args.slugs:
        if slug not in pending:
            print(f"Keeping existing {output / (slug + '.mp4')}", flush=True)
    if not pending:
        return

    source = BUNDLED_MEDIA / "source-cup.mp4"
    if not source.is_file():
        raise SystemExit(f"Bundled source clip is missing: {source}")
    source_probe = await probe_media(source)
    duration = float(source_probe["format"]["duration"])
    scratch = ROOT / "data/integration/reference-demos" / str(uuid.uuid4())
    (scratch / "source").mkdir(parents=True)
    shutil.copy2(source, scratch / "source/cup.mp4")
    report: dict = {
        "kind": "self_authored_demo",
        "source_clip": str(source.relative_to(ROOT)),
        "source_sha256": digest(source),
        "new_model_calls": 0,
        "renders": {},
    }

    for slug in pending:
        authored = json.loads((AUTHORING / f"{slug}.json").read_text())
        if authored["kind"] != "self_authored_demo":
            raise ValueError("Reference demos must be explicitly self-authored.")
        board = Storyboard.model_validate(authored["storyboard"])
        if board.target_media_job_id or board.audio_asset_id:
            raise ValueError("Offline demos may only use the bundled silent clip.")
        clips = {
            scene.scene_id: {
                "path": "source/cup.mp4",
                "duration_seconds": duration,
            }
            for scene in board.scenes
        }
        print(f"Rendering {slug} from saved authoring JSON…", flush=True)
        rendered = await render_storyboard(
            storyboard_id=board.id,
            snapshot=board.model_dump(mode="json"),
            data_dir=scratch,
            generated_clips=clips,
        )
        result = scratch / rendered.output_path
        result_probe = await probe_media(result)
        stream = next(s for s in result_probe["streams"] if s["codec_type"] == "video")
        actual_duration = float(result_probe["format"]["duration"])
        if (
            stream["width"] != 720
            or stream["height"] != 1280
            or abs(actual_duration - 15) > 0.1
        ):
            raise ValueError(
                "Rendered demo does not match its 15s / 720×1280 contract."
            )
        destination = output / f"{slug}.mp4"
        # Exclusive creation protects earlier demos even if a second run races us.
        with result.open("rb") as source_file, destination.open("xb") as target_file:
            shutil.copyfileobj(source_file, target_file)
        report["renders"][slug] = {
            "path": str(destination),
            "sha256": digest(destination),
            "duration_seconds": actual_duration,
            "width": stream["width"],
            "height": stream["height"],
            "render_ms": rendered.duration_ms,
            "authoring_path": str((AUTHORING / f"{slug}.json").relative_to(ROOT)),
        }
        (scratch / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2)
        )
        print(f"Ready: {destination}", flush=True)
    print(f"Render evidence: {scratch / 'report.json'}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", choices=SLUGS, nargs="*", default=list(SLUGS))
    parser.add_argument("--output-dir", type=Path, default=BUNDLED_MEDIA)
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except RenderError as error:
        print(error.stderr_tail, file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
