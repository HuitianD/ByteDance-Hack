import tempfile
import time
import unittest
from pathlib import Path
import cv2
import numpy as np
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app


class ApiTests(unittest.TestCase):
    def test_trial_flow_and_isolation(self):
        with tempfile.TemporaryDirectory() as t:
            settings = Settings(
                _env_file=None,
                data_dir=t,
                llm_provider="mock",
                web_dist=str(Path(t) / "none"),
            )
            app = create_app(settings)
            source = Path(t) / "fixture.mp4"
            writer = cv2.VideoWriter(
                str(source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 64)
            )
            for _ in range(20):
                writer.write(np.full((64, 64, 3), 80, np.uint8))
            writer.release()
            with TestClient(app) as c:
                self.assertEqual(c.get("/api/workspace").status_code, 401)
                code = app.state.store.create_invite(3)
                self.assertEqual(
                    c.post("/api/session", json={"code": code}).status_code, 200
                )
                token_a = c.cookies.get("viralcraft_session")
                self.assertEqual(
                    c.post("/api/session", json={"code": code}).status_code, 401
                )
                cards = c.get("/api/library").json()["cards"]
                with source.open("rb") as f:
                    r = c.post(
                        "/api/videos/upload",
                        files={"file": ("fixture.mp4", f, "video/mp4")},
                    )
                self.assertEqual(r.status_code, 201, r.text)
                upload = r.json()
                bad = c.post(
                    "/api/jobs",
                    json={
                        "kind": "generate",
                        "storyboard": {
                            "user_prompt": "Coffee",
                            "target_duration_seconds": 15,
                            "reference_card_ids": [cards[0]["id"]],
                        },
                    },
                )
                self.assertEqual(bad.status_code, 422)
                r = c.post(
                    "/api/jobs",
                    json={
                        "kind": "generate",
                        "storyboard": {
                            "user_prompt": "Coffee for your morning. Visit us.",
                            "target_duration_seconds": 15,
                            "reference_card_ids": [cards[0]["id"]],
                            "target_media_job_id": upload["id"],
                        },
                    },
                )
                self.assertEqual(r.status_code, 202, r.text)
                jid = r.json()["id"]
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    j = c.get("/api/jobs/" + jid).json()
                    if j["status"] in ("succeeded", "failed"):
                        break
                    time.sleep(0.05)
                self.assertEqual(j["status"], "succeeded", j)
                b = j["result"]
                self.assertEqual(b["target_media_job_id"], upload["id"])
                b["scenes"][0]["text"] = "Edited coffee"
                b["scenes"][0]["duration_seconds"] = 3
                payload = {k: b[k] for k in ["version", "title", "scenes"]}
                r = c.patch("/api/storyboards/" + b["id"], json=payload)
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual(r.json()["actual_duration_seconds"], 13)
                self.assertEqual(
                    c.patch("/api/storyboards/" + b["id"], json=payload).status_code,
                    409,
                )
                self.assertEqual(
                    c.post(
                        "/api/jobs",
                        json={"kind": "render", "resource_id": b["id"], "version": 1},
                    ).status_code,
                    409,
                )
                self.assertEqual(
                    c.get("/static/" + upload["saved_path"]).status_code, 404
                )
                self.assertEqual(
                    c.post("/storyboards/generate", json={}).status_code, 404
                )
                self.assertEqual(
                    c.post(
                        "/api/feedback",
                        json={"storyboard_id": b["id"], "rating": "edit"},
                        headers={"Origin": "https://evil.example"},
                    ).status_code,
                    403,
                )
                self.assertEqual(c.get(upload["url"]).status_code, 200)
                c.cookies.clear()
                c.post("/api/session", json={"code": app.state.store.create_invite(3)})
                self.assertEqual(c.get(upload["url"]).status_code, 404)
                self.assertEqual(c.get("/api/jobs/" + jid).status_code, 404)
                self.assertEqual(c.get("/api/storyboards/" + b["id"]).status_code, 404)
                self.assertEqual(c.get("/api/workspace").json()["uploads"], [])
                c.cookies.set("viralcraft_session", token_a)
                self.assertEqual(
                    c.get("/api/workspace").json()["storyboards"][0]["version"], 2
                )
