from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class StoreError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "workspace.sqlite3"
        with self.connection() as db:
            db.executescript(
                """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS invites (hash TEXT PRIMARY KEY, quota INTEGER NOT NULL, redeemed INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, expires REAL NOT NULL, quota INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS resources (id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, public INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, dedupe TEXT NOT NULL, status TEXT NOT NULL, result TEXT, error TEXT, created REAL NOT NULL, updated REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS jobs_pending ON jobs(status,created);
            CREATE TABLE IF NOT EXISTS counters (owner TEXT NOT NULL, name TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(owner,name));
            CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS provider_tasks (cache_key TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL);
            """
            )

    @contextmanager
    def connection(self, transaction=False):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            if transaction:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def create_invite(self, quota: int) -> str:
        code = secrets.token_urlsafe(18)
        with self.connection() as db:
            db.execute(
                "INSERT INTO invites(hash,quota) VALUES (?,?)", (digest(code), quota)
            )
        return code

    def redeem(self, code: str, days: int):
        token, owner = secrets.token_urlsafe(32), str(uuid.uuid4())
        with self.connection(True) as db:
            row = db.execute(
                "SELECT * FROM invites WHERE hash=? AND redeemed=0", (digest(code),)
            ).fetchone()
            if not row:
                raise StoreError("Invalid or already redeemed invitation.", 401)
            db.execute("UPDATE invites SET redeemed=1 WHERE hash=?", (digest(code),))
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?)",
                (owner, digest(token), time.time() + days * 86400, row["quota"]),
            )
        return token, owner

    def session(self, token: str | None):
        if not token:
            raise StoreError("An invitation is required to generate videos.", 401)
        with self.connection() as db:
            row = db.execute(
                "SELECT id,quota FROM sessions WHERE token_hash=? AND expires>?",
                (digest(token), time.time()),
            ).fetchone()
        if not row:
            raise StoreError("Your session expired. Please use a new invitation.", 401)
        return dict(row)

    def put_resource(
        self,
        owner: str,
        kind: str,
        body: dict,
        public=False,
        expected_version: int | None = None,
    ):
        rid = body.get("id") or body.get("job_id")
        with self.connection(True) as db:
            old = db.execute(
                "SELECT owner,body FROM resources WHERE id=?", (rid,)
            ).fetchone()
            if old and old["owner"] != owner:
                raise StoreError("Resource not found.", 404)
            if expected_version is not None and (
                not old or json.loads(old["body"]).get("version") != expected_version
            ):
                raise StoreError("This draft changed. Reload before saving.", 409)
            db.execute(
                "INSERT INTO resources VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                (rid, owner, kind, json.dumps(body), int(public), time.time()),
            )
        return body

    def resource(
        self, owner: str, rid: str, kind: str | None = None, allow_public=False
    ):
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM resources WHERE id=? AND (owner=? OR (public=1 AND ?))",
                (rid, owner, int(allow_public)),
            ).fetchone()
        if not row or kind and row["kind"] != kind:
            raise StoreError("Resource not found.", 404)
        return json.loads(row["body"])

    def resources(self, owner: str, kind: str | None = None, allow_public=False):
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM resources WHERE (owner=? OR (public=1 AND ?)) ORDER BY created DESC",
                (owner, int(allow_public)),
            ).fetchall()
        return [
            json.loads(r["body"]) for r in rows if kind is None or r["kind"] == kind
        ]

    def card_index_owner(self, owner: str, rid: str) -> str:
        """Derive search visibility from storage, not a card's descriptive origin."""
        with self.connection() as db:
            row = db.execute(
                "SELECT owner,public FROM resources WHERE id=? AND kind='card' AND (owner=? OR public=1)",
                (rid, owner),
            ).fetchone()
        if not row:
            raise StoreError("Resource not found.", 404)
        return "__public__" if row["public"] else row["owner"]

    @staticmethod
    def _consume(db, owner, name, limit, amount=1):
        row = db.execute(
            "SELECT used FROM counters WHERE owner=? AND name=?", (owner, name)
        ).fetchone()
        used = row["used"] if row else 0
        if used + amount > limit:
            raise StoreError(
                "Trial limit reached. Saved results remain available.", 429
            )
        db.execute(
            "INSERT INTO counters VALUES (?,?,?) ON CONFLICT(owner,name) DO UPDATE SET used=excluded.used",
            (owner, name, used + amount),
        )

    def reserve(
        self, owner: str, name: str, owner_limit: int, global_limit: int, amount=1
    ):
        with self.connection(True) as db:
            self._consume(db, owner, name, owner_limit, amount)
            self._consume(db, "__global__", name, global_limit, amount)

    def usage(self, owner):
        with self.connection() as db:
            return {
                r["name"]: r["used"]
                for r in db.execute(
                    "SELECT name,used FROM counters WHERE owner=?", (owner,)
                )
            }

    def enqueue(
        self,
        owner: str,
        kind: str,
        payload: dict,
        quota: int,
        global_limit: int,
        video_limit: int,
    ):
        identity = (
            [kind, payload.get("resource_id"), payload.get("version")]
            if kind == "render"
            else [kind, payload]
        )
        dedupe = digest(json.dumps(identity, sort_keys=True))
        now, jid = time.time(), str(uuid.uuid4())
        with self.connection(True) as db:
            old = db.execute(
                "SELECT * FROM jobs WHERE owner=? AND dedupe=? AND status IN ('queued','running')",
                (owner, dedupe),
            ).fetchone()
            if old:
                return self._job(old)
            active = db.execute(
                "SELECT count(*) FROM jobs WHERE owner=? AND status IN ('queued','running')",
                (owner,),
            ).fetchone()[0]
            if active >= 3:
                raise StoreError("Please wait for your current tasks to finish.", 429)
            self._consume(db, owner, "tasks", quota * 15)
            if kind == "generate":
                self._consume(db, owner, "generate", quota)
                self._consume(db, "__global__", "generate", global_limit)
            if kind in ("generate", "learn"):
                self._consume(db, owner, "planner", quota * 3)
                self._consume(db, "__global__", "planner", global_limit * 3)
            if kind == "render":
                self._consume(db, owner, "render", quota * 4)
            db.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    jid,
                    owner,
                    kind,
                    json.dumps(payload),
                    dedupe,
                    "queued",
                    None,
                    None,
                    now,
                    now,
                ),
            )
            self._event(db, owner, "job_queued", {"job_id": jid, "kind": kind})
        return self.job(owner, jid)

    @staticmethod
    def _job(row):
        return {
            "id": row["id"],
            "kind": row["kind"],
            "status": row["status"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "error": row["error"],
            "created_at": row["created"],
            "updated_at": row["updated"],
        }

    def job(self, owner, jid):
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE id=? AND owner=?", (jid, owner)
            ).fetchone()
        if not row:
            raise StoreError("Task not found.", 404)
        return self._job(row)

    def retry_payload(self, owner, jid):
        with self.connection() as db:
            row = db.execute(
                "SELECT payload,status FROM jobs WHERE id=? AND owner=?", (jid, owner)
            ).fetchone()
        if not row:
            raise StoreError("Task not found.", 404)
        if row["status"] != "failed":
            raise StoreError("Only failed tasks can be retried.", 409)
        payload = json.loads(row["payload"])
        payload.pop("snapshot", None)
        return payload

    def jobs(self, owner):
        with self.connection() as db:
            return [
                self._job(r)
                for r in db.execute(
                    "SELECT * FROM jobs WHERE owner=? ORDER BY created DESC LIMIT 50",
                    (owner,),
                )
            ]

    def claim(self):
        with self.connection(True) as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1"
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE jobs SET status='running',updated=? WHERE id=?",
                (time.time(), row["id"]),
            )
            return {**dict(row), "payload": json.loads(row["payload"])}

    def finish(self, jid, owner, result=None, error=None):
        with self.connection(True) as db:
            state = "failed" if error else "succeeded"
            db.execute(
                "UPDATE jobs SET status=?,result=?,error=?,updated=? WHERE id=?",
                (
                    state,
                    json.dumps(result) if result is not None else None,
                    error,
                    time.time(),
                    jid,
                ),
            )
            self._event(db, owner, "job_" + state, {"job_id": jid})

    def recover(self):
        with self.connection() as db:
            db.execute(
                "UPDATE jobs SET status='failed',error='Server restarted. Retry this task; saved work is available.',updated=? WHERE status='running'",
                (time.time(),),
            )

    @staticmethod
    def _event(db, owner, name, body):
        db.execute(
            "INSERT INTO events(owner,name,body,created) VALUES (?,?,?,?)",
            (owner, name, json.dumps(body), time.time()),
        )

    def event(self, owner, name, body):
        with self.connection() as db:
            self._event(db, owner, name, body)

    def provider_task(self, key, owner):
        with self.connection() as db:
            row = db.execute(
                "SELECT body FROM provider_tasks WHERE cache_key=? AND owner=?",
                (key, owner),
            ).fetchone()
        return json.loads(row["body"]) if row else None

    def save_provider_task(self, key, owner, body):
        with self.connection() as db:
            db.execute(
                "INSERT INTO provider_tasks VALUES (?,?,?) ON CONFLICT(cache_key) DO UPDATE SET body=excluded.body",
                (key, owner, json.dumps(body)),
            )
