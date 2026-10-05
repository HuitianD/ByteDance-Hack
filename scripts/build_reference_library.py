"""Opt-in visual extraction of the bundled reference videos, via the real job API.

Nothing is approved or published by this command. Completed calls are cached;
failed/uncertain calls are never automatically resubmitted. Credentials are read
only by Settings; session state stays in the ignored data directory.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.schemas.structure_card import StructureCard, ReferenceSource

CATALOG = ROOT / "packages/reference-library"
PUBLIC = ROOT / "apps/web/public/references"


def save(path, obj, private=False):
    """Replace a complete JSON file atomically; secrets are never written mode 644."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            if not private:
                os.fchmod(stream.fileno(), 0o644)
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_learn_job(client, store, owner, item, state, state_path, *, allow_paid):
    """Recover an accepted task before considering submission, including terminal tasks.

    The durable intent is written before POST. If POST or its response is lost,
    the next run either finds exactly one matching owned task or stops; it never
    repeats a possibly paid submission merely because a job ID is missing.
    """
    upload_id = item["upload_id"]
    store.resource(owner, upload_id, "upload")
    with store.connection() as db:
        rows = db.execute(
            "SELECT id,payload FROM jobs WHERE owner=? AND kind='learn' ORDER BY created",
            (owner,),
        ).fetchall()
    matches = [
        row["id"]
        for row in rows
        if json.loads(row["payload"]).get("resource_id") == upload_id
    ]
    if item.get("job_id"):
        if item["job_id"] not in matches:
            raise SystemExit(
                "Saved task does not match this owner's source upload; refusing resubmission."
            )
        return item["job_id"]
    if len(matches) > 1:
        raise SystemExit(
            "Multiple matching tasks exist. Inspect them before continuing; no task submitted."
        )
    if matches:
        item["job_id"] = matches[0]
        item["submission_state"] = "submitted"
        save(state_path, state, True)
        return matches[0]
    if item.get("submission_state"):
        raise SystemExit(
            "A prior submission intent exists but no matching task can be confirmed. "
            "Inspect the isolated task database before any retry; no task submitted."
        )
    if not allow_paid:
        raise SystemExit("New visual call requires --allow-paid.")
    item["submission_state"] = "submitting"
    item["submission_started_at"] = time.time()
    save(state_path, state, True)
    response = client.post(
        "/api/jobs", json={"kind": "learn", "resource_id": upload_id}
    )
    response.raise_for_status()
    job_id = response.json()["id"]
    # Verify the response belongs to the actual task accepted into this store.
    with store.connection() as db:
        accepted = db.execute(
            "SELECT payload FROM jobs WHERE id=? AND owner=? AND kind='learn'",
            (job_id, owner),
        ).fetchone()
    if (
        accepted is None
        or json.loads(accepted["payload"]).get("resource_id") != upload_id
    ):
        raise SystemExit(
            "Task response could not be reconciled; durable submission intent retained."
        )
    item["job_id"] = job_id
    item["submission_state"] = "submitted"
    save(state_path, state, True)
    return job_id


def wait(client, jid):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        response = client.get("/api/jobs/" + jid)
        response.raise_for_status()
        job = response.json()
        if job["status"] == "failed":
            raise RuntimeError("Extraction failed; no automatic retry: " + job["error"])
        if job["status"] == "succeeded":
            return job["result"]
        time.sleep(0.5)
    raise TimeoutError(
        "Task not finished. Run the command again to inspect the same task."
    )


def main():
    from app.main import create_app

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-paid",
        action="store_true",
        help="Allow at most one new Seed image call per selected reference.",
    )
    parser.add_argument("--slug", choices=["showcase", "question", "list"])
    parser.add_argument(
        "--data-dir", default=str(ROOT / "data/integration/reference-library")
    )
    args = parser.parse_args()
    manifest = json.loads((CATALOG / "manifest.json").read_text())
    entries = [
        e for e in manifest["references"] if not args.slug or e["slug"] == args.slug
    ]
    work = Path(args.data_dir).resolve()
    state_path = work / "import-state.private.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"items": {}}
    settings = Settings(
        data_dir=str(work),
        seedance_enabled=False,
        database_url=None,
        global_generation_limit=3,
    )
    if settings.llm_provider != "seed" or settings.missing_for_provider():
        raise SystemExit(
            "Configure a real Seed vision-capable model in apps/api/.env first."
        )
    app = create_app(settings)
    with TestClient(app) as client:
        if "token" not in state:
            response = client.post(
                "/api/session", json={"code": app.state.store.create_invite(3)}
            )
            response.raise_for_status()
            state["token"] = response.cookies["viralcraft_session"]
            save(state_path, state, True)
        client.cookies.set("viralcraft_session", state["token"])
        client.get("/api/session").raise_for_status()
        owner = app.state.store.session(state["token"])["id"]
        for entry in entries:
            slug = entry["slug"]
            source = PUBLIC / (slug + ".mp4")
            checksum = hashlib.sha256(source.read_bytes()).hexdigest()
            item = state["items"].get(slug, {})
            if item and item["sha256"] != checksum:
                raise SystemExit(
                    "Reference changed. Use a new isolated data directory to retain the old evidence."
                )
            if not item:
                if not args.allow_paid:
                    raise SystemExit(
                        "New visual call requires --allow-paid. No model was called."
                    )
                with source.open("rb") as f:
                    # Do not tell the analyzer which pattern the author intended.
                    response = client.post(
                        "/api/videos/upload",
                        files={"file": ("reference.mp4", f, "video/mp4")},
                    )
                response.raise_for_status()
                item = {"upload_id": response.json()["id"], "sha256": checksum}
                state["items"][slug] = item
                save(state_path, state, True)
            ensure_learn_job(
                client,
                app.state.store,
                owner,
                item,
                state,
                state_path,
                allow_paid=args.allow_paid,
            )
            print(f"{slug}: inspecting saved task", flush=True)
            card = StructureCard.model_validate(wait(client, item["job_id"]))
            analysis_path = (
                work / "knowledge_base" / item["upload_id"] / "video_analysis.json"
            )
            analysis = json.loads(analysis_path.read_text())
            card.source = ReferenceSource(
                kind="self_authored_demo",
                title=entry["title"],
                author="ViralCraft — AI-assisted demonstration",
                media_url=f"/references/{slug}.mp4",
                sha256=checksum,
                original_duration_seconds=analysis["duration_seconds"],
                excerpt_end_seconds=analysis["duration_seconds"],
                changes=entry["provenance"],
            )
            for frame in card.evidence_frames:
                original = next(
                    f for f in analysis["frames"] if f["index"] == frame.index
                )
                relative = f"{slug}/frame_{frame.index:03d}.jpg"
                destination = PUBLIC / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(work / original["path"], destination)
                frame.url = "/references/" + relative
            # Export objective scene boundaries for future evidence validation.
            analysis["source_video_path"] = card.source.media_url
            by_index = {f.index: f.url for f in card.evidence_frames}
            for frame in analysis["frames"]:
                frame["path"] = by_index.get(frame["index"], "not_in_model_input")
            for scene in analysis["scenes"]:
                scene["thumbnail_path"] = None
            raw_path = CATALOG / "extractions" / (slug + ".json")
            body = card.model_dump(mode="json")
            if raw_path.exists() and json.loads(raw_path.read_text()) != body:
                raise SystemExit(
                    "Refusing to overwrite a different raw extraction. Archive it explicitly first."
                )
            save(raw_path, body)
            save(CATALOG / "analyses" / (slug + ".json"), analysis)
            with app.state.store.connection() as db:
                events = [
                    json.loads(r["body"])
                    for r in db.execute(
                        "SELECT body FROM events WHERE name='planner_usage' ORDER BY id"
                    )
                ]
            save(work / "usage.json", events)
            print(
                json.dumps(
                    {
                        "slug": slug,
                        "mode": card.analysis.mode,
                        "frames": len(card.evidence_frames),
                        "observations": len(card.observations),
                        "rules": len(card.rules),
                        "review": card.review.status,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    print(
        "Raw extractions saved. Review frames and observations before publishing any card."
    )


if __name__ == "__main__":
    main()
