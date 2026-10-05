"""Exercise invitation -> sample upload -> queued draft -> edits -> real MP4.
Defaults to mock planning in an isolated directory; never calls paid providers.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app


def wait(client, job_id):
    deadline = time.monotonic() + 660
    while time.monotonic() < deadline:
        r = client.get("/api/jobs/" + job_id)
        r.raise_for_status()
        job = r.json()
        if job["status"] == "failed":
            raise RuntimeError(job["error"])
        if job["status"] == "succeeded":
            return job["result"]
        time.sleep(0.5)
    raise TimeoutError("Smoke task did not finish.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/tmp/viralcraft-relaunch-smoke")
    parser.add_argument("--renders", type=int, default=2)
    args = parser.parse_args()
    settings = Settings(
        _env_file=None,
        llm_provider="mock",
        data_dir=args.data_dir,
        web_dist=str(ROOT / "apps/web/out"),
    )
    app = create_app(settings)
    reports = []
    with TestClient(app, base_url="https://testserver") as c:
        c.post(
            "/api/session", json={"code": app.state.store.create_invite(3)}
        ).raise_for_status()
        c.post("/api/demo").raise_for_status()
        upload = c.get("/api/workspace").json()["uploads"][0]
        cards = c.get("/api/library").json()["cards"]
        for i, prompt in enumerate(
            [
                "Fresh coffee for slow mornings. Visit Craft this weekend.",
                "一杯咖啡，开启你的早晨。欢迎周末到店。",
                "Fresh roast, a quiet break, and a cup worth sharing. Visit Craft.",
            ][: args.renders]
        ):
            j = c.post(
                "/api/jobs",
                json={
                    "kind": "generate",
                    "storyboard": {
                        "user_prompt": prompt,
                        "target_duration_seconds": 15 if i == 0 else 20,
                        "reference_card_ids": [cards[i % len(cards)]["id"]],
                        "target_media_job_id": upload["id"],
                    },
                },
            )
            j.raise_for_status()
            b = wait(c, j.json()["id"])
            b["scenes"][0]["text"] = (
                "Your morning, reimagined" if i == 0 else "给早晨一点好味道"
            )
            b["scenes"][-1]["text"] = (
                "Visit us this weekend" if i == 0 else "这个周末，来喝一杯"
            )
            b["scenes"][1]["text"] = (
                "Freshly roasted coffee" if i == 0 else "新鲜烘焙，慢慢品尝"
            )
            edited = c.patch(
                "/api/storyboards/" + b["id"],
                json={k: b[k] for k in ("version", "title", "scenes")},
            )
            edited.raise_for_status()
            b = edited.json()
            j = c.post(
                "/api/jobs",
                json={
                    "kind": "render",
                    "resource_id": b["id"],
                    "version": b["version"],
                },
            )
            j.raise_for_status()
            r = wait(c, j.json()["id"])
            media = c.get("/api/media/" + r["id"])
            media.raise_for_status()
            report = {
                "storyboard_id": b["id"],
                "render_id": r["id"],
                "output": str(Path(args.data_dir) / r["output_path"]),
                "version": r["version"],
                "render_ms": r["duration_ms"],
                "size": len(media.content),
            }
            reports.append(report)
            print(json.dumps(report), flush=True)
    Path(args.data_dir, "smoke-report.json").write_text(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
