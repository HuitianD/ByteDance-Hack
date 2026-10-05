"""Generate our own synthetic demo footage; no downloads or third-party media."""

from pathlib import Path
import math
import os
import shutil
import subprocess
import tempfile
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "apps/api/demo/sample.mp4"
out.parent.mkdir(parents=True, exist_ok=True)
ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    candidates = list((ROOT / "node_modules/@remotion").glob("compositor-*/ffmpeg"))
    ffmpeg = str(candidates[0]) if candidates else None
if not ffmpeg:
    raise SystemExit("FFmpeg is required to build demo media.")
with tempfile.TemporaryDirectory() as temp:
    raw = Path(temp) / "demo.avi"
    w, h, fps = 360, 640, 24
    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    for frame in range(15 * fps):
        t = frame / fps
        image = np.zeros((h, w, 3), np.uint8)
        for y in range(h):
            image[y, :] = (
                int(20 + y * 0.025),
                int(32 + y * 0.035),
                int(41 + y * 0.045),
            )
        shift = int(12 * math.sin(t * 0.7))
        cx = 180 + shift
        cy = 330
        cv2.ellipse(image, (cx, cy + 150), (95, 18), 0, 0, 360, (12, 20, 28), -1)
        cv2.rectangle(
            image, (cx - 58, cy - 90), (cx + 58, cy + 120), (168, 194, 205), -1
        )
        cv2.ellipse(image, (cx, cy - 90), (58, 13), 0, 0, 360, (188, 211, 220), -1)
        cv2.rectangle(image, (cx - 50, cy - 25), (cx + 50, cy + 62), (48, 74, 83), -1)
        cv2.putText(
            image,
            "CRAFT",
            (cx - 41, cy + 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (240, 241, 238),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            "COFFEE",
            (cx - 35, cy + 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.32,
            (210, 223, 228),
            1,
            cv2.LINE_AA,
        )
        for i in range(3):
            sx = cx - 25 + i * 25 + int(8 * math.sin(t * 1.2 + i))
            sy = cy - 120 - int((t * 20 + i * 12) % 65)
            cv2.ellipse(
                image, (sx, sy), (8, 17), 15, 0, 180, (116, 133, 147), 1, cv2.LINE_AA
            )
        cv2.putText(
            image,
            "SYNTHETIC DEMO FOOTAGE",
            (40, 590),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (140, 157, 170),
            1,
            cv2.LINE_AA,
        )
        writer.write(image)
    writer.release()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(raw),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ],
        check=True,
        env={**os.environ, "DYLD_LIBRARY_PATH": str(Path(ffmpeg).parent)},
    )
public = ROOT / "apps/web/public/examples"
public.mkdir(parents=True, exist_ok=True)
shutil.copy2(out, public / "source.mp4")
# Docker builds the frontend before the deterministic fixture; install into export too.
export = ROOT / "apps/web/out/examples"
if export.parent.exists():
    export.mkdir(exist_ok=True)
    shutil.copy2(out, export / "source.mp4")
print(out)
