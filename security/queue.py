"""One durable, bounded append-only ingestion supervisor; no remote shell or delete."""
from __future__ import annotations

import hashlib
import fcntl
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from security.store import AccessError
from security import sandbox
from runtime_support import atomic_json
from security.job_state import CATEGORIES, detail

log = logging.getLogger("bifrost.queue")


class IngestQueue:
    def __init__(self, store, project: Path, env_file: Path):
        self.store, self.project, self.env_file = store, project, env_file
        self.stop_event, self.lock, self.process = threading.Event(), threading.Lock(), None
        self.thread = None
        self.owner_lock = None
        with store.transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, principal TEXT, idempotency TEXT, fingerprint TEXT,
                kind TEXT, payload TEXT, size INTEGER, status TEXT, created REAL,
                attempts INTEGER DEFAULT 0, next_attempt REAL DEFAULT 0, returncode INTEGER,
                UNIQUE(principal,idempotency))""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)")}
            for name, definition in {"error_category": "TEXT", "claimed_at": "REAL", "owner_retries": "INTEGER DEFAULT 0"}.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")

    def submit(self, principal, kind: str, payload: dict, idempotency: str | None) -> dict:
        sandbox.available()
        if not self.env_file.is_file() or not (self.project / ".venv/bin/python").is_file():
            raise AccessError("API ingestion requires the append-only worker configuration", 503)
        if idempotency and (len(idempotency) > 128 or not idempotency.isascii()):
            raise AccessError("Idempotency-Key must be at most 128 ASCII characters", 400)
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256((kind + body).encode()).hexdigest()
        size = self.store.limits["url_payload_quota_bytes"] if kind == "url" else len(body.encode())
        with self.store.transaction() as db:
            old = db.execute("SELECT id,fingerprint FROM jobs WHERE principal=? AND idempotency=?", (principal.id, idempotency)).fetchone() if idempotency else None
            if old:
                if old["fingerprint"] != fingerprint:
                    raise AccessError("Idempotency-Key already belongs to a different submission", 409)
                return {"ok": True, "job_id": old["id"], "url": payload.get("url"), "duplicate": True}
            active = db.execute("SELECT principal FROM jobs WHERE status IN ('queued','running')").fetchall()
            cfg = self.store.limits
            if db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] >= cfg["retained_jobs"]:
                raise AccessError("Retained job limit reached; owner maintenance required", 429, 3600)
            if len(active) >= cfg["queue_capacity"] or sum(r[0] == principal.id for r in active) >= cfg["key_pending_jobs"]:
                raise AccessError("Ingestion queue is full; retry later", 429, 60)
            stored = db.execute("SELECT COALESCE(SUM(size),0) FROM jobs").fetchone()[0]
            if stored + size > cfg["queue_payload_bytes"]:
                raise AccessError("Retained job budget is full; owner maintenance required", 429, 3600)
            self.store.submission_quota(db, principal, size)
            id = uuid.uuid4().hex
            db.execute("INSERT INTO jobs(id,principal,idempotency,fingerprint,kind,payload,size,status,created) VALUES (?,?,?,?,?,?,?,'queued',?)",
                       (id, principal.id, idempotency, fingerprint, kind, body, size, time.time()))
        log.info("admitted job=%s client=%s kind=%s", id, principal.id, kind)
        return {"ok": True, "job_id": id, "url": payload.get("url"), "status": "queued"}

    def states(self, principal, id: str | None = None) -> list[dict]:
        with self.store.transaction() as db:
            rows = db.execute("SELECT * FROM jobs WHERE (? OR principal=?) AND (? IS NULL OR id=?) ORDER BY created DESC LIMIT 100",
                              ("admin" in principal.scopes, principal.id, id, id)).fetchall()
        return [{"job_id": r["id"], "url": json.loads(r["payload"]).get("url"),
                 "title": json.loads(r["payload"]).get("title"),
                 "status": r["status"], "started_at": datetime.fromtimestamp(r["created"]).isoformat(), "returncode": r["returncode"],
                 **detail(dict(r), self.store.directory),
                 "attempts": r["attempts"], "log_tail": "See private worker logs for details" if r["status"] == "failed" else ""} for r in rows]

    def retry(self, id: str) -> dict:
        with self.store.transaction() as db:
            row = db.execute("SELECT j.*,k.revoked,k.expires,k.scopes FROM jobs j JOIN keys k ON k.id=j.principal WHERE j.id=?", (id,)).fetchone()
            if not row:
                raise AccessError("No such job", 404)
            if row["status"] != "failed":
                raise AccessError("Only failed jobs can be retried", 409)
            if row["revoked"] or (row["expires"] and row["expires"] <= time.time()) or "ingest" not in json.loads(row["scopes"]):
                raise AccessError("Original submitting key is no longer authorized", 403)
            cfg = self.store.limits
            if row["owner_retries"] >= cfg["owner_job_retries"]:
                raise AccessError("Owner retry budget exhausted; inspect and deliberately resubmit", 409)
            active = db.execute("SELECT principal FROM jobs WHERE status IN ('queued','running')").fetchall()
            if len(active) >= cfg["queue_capacity"] or sum(r[0] == row["principal"] for r in active) >= cfg["key_pending_jobs"]:
                raise AccessError("Ingestion queue is full", 429, 60)
            db.execute("UPDATE jobs SET status='queued',attempts=0,next_attempt=0,returncode=NULL,error_category=NULL,owner_retries=owner_retries+1 WHERE id=?", (id,))
        log.info("owner requeued job=%s", id)
        return {"ok": True, "job_id": id, "status": "queued"}

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        ownership = (self.store.directory / "queue.lock").open("a")
        ownership_path = self.store.directory / "queue.lock"
        ownership_path.chmod(0o600)
        try:
            fcntl.flock(ownership, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            ownership.close()
            raise AccessError("Another server owns this ingestion queue", 503) from None
        self.owner_lock = ownership
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, name="bifrost-ingest", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        with self.lock:
            self._kill()
        if self.thread:
            self.thread.join(timeout=10)
        if self.owner_lock and not (self.thread and self.thread.is_alive()):
            self.owner_lock.close()
            self.owner_lock = None

    def snapshot(self) -> dict:
        with self.store.transaction() as db:
            counts = {row[0]: row[1] for row in db.execute("SELECT status,count(*) FROM jobs GROUP BY status")}
            retained = db.execute("SELECT count(*),coalesce(sum(size),0) FROM jobs").fetchone()
        return {"counts": counts, "retained_jobs": retained[0], "reserved_bytes": retained[1],
                "supervisor_alive": bool(self.thread and self.thread.is_alive()),
                "queue_capacity": self.store.limits["queue_capacity"],
                "retained_capacity": self.store.limits["retained_jobs"]}

    def _kill(self):
        if self.process and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def _claim(self):
        with self.store.transaction() as db:
            # Only this serial supervisor executes jobs. Repair an interrupted
            # state update before claiming another job after a store outage.
            db.execute("UPDATE jobs SET status='queued' WHERE status='running'")
            row = db.execute("SELECT * FROM jobs WHERE status='queued' AND next_attempt<=? ORDER BY created LIMIT 1", (time.time(),)).fetchone()
            if row:
                db.execute("UPDATE jobs SET status='running', attempts=attempts+1,claimed_at=? WHERE id=?", (time.time(), row["id"]))
                return dict(row)

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                job = self._claim()
                if job:
                    self._execute(job)
                else:
                    self.stop_event.wait(1)
            except Exception:
                log.warning("queue supervision failed; retrying", exc_info=True)
                self.stop_event.wait(5)

    def _active(self, id):
        with self.store.transaction() as db:
            row = db.execute("SELECT expires,revoked,scopes FROM keys WHERE id=?", (id,)).fetchone()
        return row and not row["revoked"] and (not row["expires"] or row["expires"] > time.time()) and "ingest" in json.loads(row["scopes"])

    def _command(self, job):
        payload = json.loads(job["payload"])
        target, payload_path = payload.get("url"), None
        if job["kind"] == "text":
            payload_path = self.store.directory / (job["id"] + ".txt")
            payload_path.write_text(payload["text"], encoding="utf-8")
            payload_path.chmod(0o600)
            target = "/payload.txt"
        env = sandbox.environment(job, payload.get("title", ""))
        cfg = dict(self.store.limits)
        used = sum(path.stat().st_size for path in self.store.directory.glob("*.log"))
        free = cfg["worker_total_log_bytes"] - used
        if free <= 0:
            raise AccessError("Private worker log budget exhausted; owner maintenance required")
        path = self.store.directory / (job["id"] + ".log")
        current = path.stat().st_size if path.exists() else 0
        cfg["worker_log_bytes"] = min(cfg["worker_log_bytes"], current + free)
        limits_file = self.store.directory / "worker-limits.json"
        atomic_json(limits_file, cfg)
        isolated = sandbox.command(self.project, self.env_file, payload_path, limits_file, cfg["worker_tmp_bytes"])
        command = [sys.executable, str(Path(__file__).with_name("worker.py")), json.dumps(cfg),
                   *isolated, "--", str(self.project / ".venv/bin/python"), str(self.project / "ingest.py"), "add", target]
        return command, env

    def _execute(self, job):
        code = 1
        active = True
        category = None
        try:
            active = self._active(job["principal"])
            if not active:
                raise AccessError("Submitting key expired or was revoked")
            command, env = self._command(job)
            path = self.store.directory / (job["id"] + ".log")
            with path.open("a") as stream, self.lock:
                path.chmod(0o600)
                if self.stop_event.is_set():
                    return
                self.process = subprocess.Popen(command, cwd=self.project, env=env,
                                                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = self.process.wait(timeout=self.store.limits["worker_timeout_seconds"])
            except subprocess.TimeoutExpired:
                with self.lock:
                    self._kill()
                self.process.wait(timeout=5)
                code, category = 124, "timeout"
                log.warning("worker deadline exceeded job=%s", job["id"])
        except AccessError:
            active = False
            category = "policy"
            log.warning("ingestion policy prevented job=%s", job["id"])
        except Exception:
            log.warning("ingestion worker failed job=%s", job["id"], exc_info=True)
        if self.stop_event.is_set():
            return  # restart requeues interrupted jobs; hash dedup makes replay safe
        self._finish(job, code, active, category)

    def _finish(self, job, code, active, category):
        attempt = job["attempts"] + 1
        category = category or (CATEGORIES.get(code, "unexpected") if code != 0 else None)
        retry = code not in (0, 21, 22) and active and attempt < self.store.limits["job_attempts"]
        with self.store.transaction() as db:
            db.execute("UPDATE jobs SET status=?,returncode=?,next_attempt=?,error_category=? WHERE id=?",
                       ("queued" if retry else "ok" if code == 0 else "failed", code,
                        time.time() + self.store.limits["retry_seconds"] * 2 ** min(attempt - 1, 16) if retry else 0, category, job["id"]))
        log.info("worker job=%s exit=%s attempt=%s retry=%s", job["id"], code, attempt, retry)
