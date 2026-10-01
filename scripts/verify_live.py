"""Opt-in paid integration checks, with persistent jobs and no automatic resubmission.

Run draft, assets, then render. Reads apps/api/.env. A completed stage is reused.
Private session state stays in gitignored DATA_DIR with mode 0600.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["draft", "assets", "render"])
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--resume-assets",
        action="store_true",
        help="Explicitly recheck a completed assets job that returned warnings; provider state prevents duplicate submissions.",
    )
    parser.add_argument("--run", default="local-live-2026-09-30")
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error(
            "Real model calls require --allow-paid; existing smoke_trial.py remains offline."
        )
    if not args.run.replace("-", "").isalnum():
        parser.error("Use a simple alphanumeric run name.")
    settings = Settings()
    if settings.llm_provider != "seed" or settings.seedance_provider != "seedance":
        parser.error(
            "This check requires real providers; mock results are not accepted."
        )
    folder = settings.data_dir_path() / "integration" / args.run
    folder.mkdir(parents=True, exist_ok=True)
    private = folder / "session.json"
    report_path = folder / "report.json"
    state = json.loads(private.read_text()) if private.exists() else {"jobs": {}}
    report = json.loads(report_path.read_text()) if report_path.exists() else {}

    def save():
        # Create restrictive temporary files before writing the session token.
        temp = private.with_suffix(".tmp")
        fd = os.open(temp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        temp.replace(private)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    app = create_app(settings)
    with TestClient(app, base_url="http://localhost") as c:
        if "token" not in state:
            r = c.post("/api/session", json={"code": app.state.store.create_invite(3)})
            r.raise_for_status()
            state["token"] = c.cookies.get("viralcraft_session")
            save()
        else:
            c.cookies.set("viralcraft_session", state["token"])
            c.get("/api/session").raise_for_status()

        def job(label, payload):
            if label not in state["jobs"]:
                r = c.post("/api/jobs", json=payload)
                if r.status_code != 202:
                    raise RuntimeError(
                        f"Job rejected: {r.status_code}; {r.json().get('detail')}"
                    )
                state["jobs"][label] = r.json()["id"]
                save()
            jid = state["jobs"][label]
            j = c.get("/api/jobs/" + jid).json()
            if j["status"] == "failed" and args.retry_failed:
                r = c.post("/api/jobs/" + jid + "/retry")
                r.raise_for_status()
                jid = state["jobs"][label] = r.json()["id"]
                save()
            last = None
            deadline = time.monotonic() + 750
            while time.monotonic() < deadline:
                j = c.get("/api/jobs/" + jid).json()
                if j["status"] != last:
                    print(label, j["status"], flush=True)
                    last = j["status"]
                if last in ("succeeded", "failed"):
                    report[label + "_job"] = {
                        k: j[k]
                        for k in ("id", "status", "created_at", "updated_at", "error")
                    }
                    save()
                    if last == "failed":
                        raise RuntimeError(j["error"])
                    return j["result"]
                time.sleep(2)
            raise TimeoutError(
                "Task ID saved. Inspect it before retrying; no new video submission is needed."
            )

        if args.stage == "draft":
            if "upload_id" not in state:
                r = c.post("/api/demo")
                r.raise_for_status()
                state["upload_id"] = r.json()["id"]
                save()
            queries = [
                "Sensory product reveal: coffee close-up, aroma and detail, then invitation.",
                "Three reasons to try: a clear promise, a numbered list of benefits, then CTA.",
            ]
            for i, query in enumerate(queries):
                key = "retrieval_" + str(i + 1)
                if key in report:
                    continue
                r = c.post("/api/library/search", json={"query": query})
                r.raise_for_status()
                result = r.json()
                if result["mode"] != "semantic":
                    raise RuntimeError(
                        "Real embedding/SQL retrieval failed; manual fallback is not a passing result."
                    )
                report[key] = {
                    "query": query,
                    "mode": result["mode"],
                    "cards": [
                        {"id": x["id"], "name": x["pattern_name"]}
                        for x in result["cards"]
                    ],
                }
                save()
                print(key, report[key], flush=True)
            refs = [x["id"] for x in report["retrieval_1"]["cards"]]
            board = job(
                "draft",
                {
                    "kind": "generate",
                    "storyboard": {
                        "user_prompt": "为虚构咖啡店 Craft 制作15秒中文短片。素材是自制的咖啡杯演示动画，并非实拍。结构为开场、细节、邀请，恰好3个场景，每场5秒。字幕简短中文，最后邀请周末到店；不添加未经提供的功效或价格。asset_prompt 使用英文，描述无人物、无文字、无logo的陶瓷咖啡杯与蒸汽特写，适合5秒产品镜头。",
                        "target_duration_seconds": 15,
                        "reference_card_ids": refs,
                        "target_media_job_id": state["upload_id"],
                    },
                },
            )
            assert board["generation_mode"] == "seed"
            assert all(x["source_structure_card_id"] in refs for x in board["scenes"])
            state["board_id"] = board["id"]
            report["draft"] = {
                "id": board["id"],
                "generation_mode": board["generation_mode"],
                "model": settings.seed_model,
                "reference_card_ids": refs,
                "scene_references": [
                    x["source_structure_card_id"] for x in board["scenes"]
                ],
                "scene_count": len(board["scenes"]),
                "duration": board["actual_duration_seconds"],
            }
            save()
        else:
            if "board_id" not in state:
                raise RuntimeError("Run the draft stage first.")
            board = c.get("/api/storyboards/" + state["board_id"]).json()
            if args.stage == "assets":
                if args.resume_assets:
                    previous = state["jobs"].get("assets")
                    if previous:
                        old = c.get("/api/jobs/" + previous).json()
                        if old["status"] != "succeeded" or old.get("result", {}).get(
                            "attached"
                        ):
                            raise RuntimeError(
                                "Only an assets job with no attached clips can be resumed this way."
                            )
                        state.setdefault("previous_assets_jobs", []).append(previous)
                        del state["jobs"]["assets"]
                        save()
                result = job(
                    "assets",
                    {
                        "kind": "assets",
                        "resource_id": board["id"],
                        "version": board["version"],
                        "scene_ids": [board["scenes"][0]["scene_id"]],
                    },
                )
                report["assets"] = result
                save()
                if not result["attached"]:
                    raise RuntimeError(
                        result["warnings"] or "No real generated clip was attached."
                    )
                owner = app.state.store.session(state["token"])["id"]
                assets = [
                    app.state.store.resource(owner, aid, "asset")
                    for aid in result["attached"].values()
                ]
                assert len(assets) == 1 and not assets[0]["mock"]
                report["generated_clip"] = assets[0]
                save()
            else:
                if not any(x.get("generated_asset_id") for x in board["scenes"]):
                    raise RuntimeError(
                        "A real generated clip must be attached before final rendering."
                    )
                result = job(
                    "render",
                    {
                        "kind": "render",
                        "resource_id": board["id"],
                        "version": board["version"],
                    },
                )
                media = c.get("/api/media/" + result["id"])
                media.raise_for_status()
                report["render"] = {
                    "id": result["id"],
                    "version": result["version"],
                    "output": str(settings.data_dir_path() / result["output_path"]),
                    "bytes": len(media.content),
                    "render_ms": result["duration_ms"],
                }
                save()
        owner = app.state.store.session(state["token"])["id"]
        with app.state.store.connection() as db:
            report["usage_events"] = [
                {"name": row["name"], "body": json.loads(row["body"])}
                for row in db.execute(
                    "SELECT name,body FROM events WHERE owner=? AND name IN ('planner_usage','embedding_usage','retrieval','video_usage') ORDER BY id",
                    (owner,),
                )
            ]
        save()
        print("Verified stage:", args.stage, "Report:", report_path, flush=True)


if __name__ == "__main__":
    main()
