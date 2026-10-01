"""SQLite transactions own credentials and recovery; source knowledge is untouched."""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


class AccessError(Exception):
    def __init__(self, message: str, status: int = 403, retry: int = 0):
        super().__init__(message)
        self.status, self.retry = status, retry


@dataclass(frozen=True)
class Principal:
    id: str
    scopes: frozenset[str]
    rpm: int
    writes: int
    documents: int
    bytes: int


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def load_limits() -> dict:
    values = json.loads(Path(__file__).with_name("limits.json").read_text())
    if os.getenv("VIEWER_LIMITS_FILE"):
        override = json.loads(Path(os.environ["VIEWER_LIMITS_FILE"]).read_text())
        if not isinstance(override, dict) or set(override) - set(values):
            raise ValueError("security limits override contains unknown settings")
        values.update(override)
    if any(type(v) is not int or v <= 0 for v in values.values()):
        raise ValueError("security limits must be positive integers")
    return values


class SecurityStore:
    def __init__(self, directory: Path, legacy_token: str, email: str = ""):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        self.path = directory / "access.sqlite3"
        self.limits = load_limits()
        with contextlib.closing(sqlite3.connect(self.path)) as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS keys (
              id TEXT PRIMARY KEY, hash TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
              scopes TEXT NOT NULL, expires REAL, revoked INTEGER DEFAULT 0,
              rpm INTEGER NOT NULL, writes INTEGER NOT NULL,
              documents INTEGER NOT NULL, bytes INTEGER NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS usage (
              id TEXT, window TEXT, requests INTEGER DEFAULT 0, documents INTEGER DEFAULT 0,
              bytes INTEGER DEFAULT 0, PRIMARY KEY(id,window));
            CREATE TABLE IF NOT EXISTS challenges (
              hash TEXT PRIMARY KEY, purpose TEXT, payload TEXT, expires REAL,
              used INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, event TEXT, subject TEXT);
            """)
        with self.transaction() as db:
            if not db.execute("SELECT 1 FROM keys WHERE id='owner'").fetchone():
                self._rotate_owner(db)
                self._set(db, "email", email)
                self._set(db, "email_verified", False)
                if legacy_token:
                    self._insert_key(db, "legacy", legacy_token, "Legacy read access", ["read"],
                                     time.time() + self.limits["legacy_grace_days"] * 86400,
                                     rpm=self.limits["owner_requests_per_minute"])
        self.path.chmod(0o600)

    @contextlib.contextmanager
    def transaction(self):
        with contextlib.closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("BEGIN IMMEDIATE")
            yield db

    def _set(self, db, name: str, value: object) -> None:
        db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (name, json.dumps(value)))

    def _audit(self, db, event: str, subject: str) -> None:
        db.execute("INSERT INTO audit(at,event,subject) VALUES (?,?,?)", (time.time(), event, subject))
        db.execute("DELETE FROM audit WHERE id < (SELECT COALESCE(MAX(id),0)-1000 FROM audit)")

    def setting(self, name: str, default=None):
        with self.transaction() as db:
            row = db.execute("SELECT value FROM meta WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, name: str, value: object) -> None:
        with self.transaction() as db:
            self._set(db, name, value)

    def _insert_key(self, db, id: str, token: str, name: str, scopes: list[str], expires, **limits) -> None:
        owner = id == "owner"
        cfg = self.limits
        db.execute("INSERT OR REPLACE INTO keys VALUES (?,?,?,?,?,0,?,?,?,?,?)", (
            id, digest(token), name, json.dumps(scopes), expires,
            limits.get("rpm", cfg["owner_requests_per_minute"] if owner else cfg["ai_requests_per_minute"]),
            limits.get("writes", cfg["ai_writes_per_minute"]),
            limits.get("documents", cfg["ai_documents_per_day"]),
            limits.get("bytes", cfg["ai_bytes_per_day"]), time.time()))

    def _rotate_owner(self, db) -> str:
        token = "bfo_" + secrets.token_urlsafe(32)
        self._insert_key(db, "owner", token, "Owner", ["read", "ingest", "admin"], None)
        self._set(db, "launcher_token", token)
        self._audit(db, "owner_rotated", "owner")
        return token

    def owner_token(self) -> str:
        return self.setting("launcher_token")

    def authenticate(self, token: str) -> Principal:
        if not token or len(token) > 256:
            raise AccessError("Invalid or missing access token", 401)
        with self.transaction() as db:
            row = db.execute("SELECT * FROM keys WHERE hash=?", (digest(token),)).fetchone()
        if not row or not secrets.compare_digest(row["hash"], digest(token)) or row["revoked"] or (row["expires"] and row["expires"] <= time.time()):
            raise AccessError("Invalid or expired access token", 401)
        return Principal(row["id"], frozenset(json.loads(row["scopes"])), row["rpm"], row["writes"], row["documents"], row["bytes"])

    def create_key(self, name: str, scopes: list[str], days: int, **limits) -> dict:
        if not name.strip() or len(name) > 120 or not scopes or not set(scopes) <= {"read", "ingest"}:
            raise AccessError("AI keys may grant only read and ingest scopes", 400)
        if not 1 <= days <= 365:
            raise AccessError("Expiry must be between 1 and 365 days", 400)
        if any(not isinstance(value, int) or not 1 <= value <= self.limits[maximum]
               for key, value in limits.items()
               for maximum in [{"rpm": "ai_requests_per_minute", "writes": "ai_writes_per_minute",
                                "documents": "ai_documents_per_day", "bytes": "ai_bytes_per_day"}[key]]):
            raise AccessError("Key quotas must be positive and within server limits", 400)
        token, id = "bfa_" + secrets.token_urlsafe(32), secrets.token_hex(12)
        with self.transaction() as db:
            if db.execute("SELECT COUNT(*) FROM keys WHERE revoked=0 AND id!='owner'").fetchone()[0] >= self.limits["active_keys"]:
                raise AccessError("Active key limit reached; revoke unused keys", 429)
            self._insert_key(db, id, token, name.strip(), scopes, time.time() + days * 86400, **limits)
            self._audit(db, "key_created", id)
        return {"id": id, "token": token, "scopes": scopes}

    def list_keys(self) -> list[dict]:
        with self.transaction() as db:
            rows = db.execute("SELECT id,name,scopes,expires,revoked,rpm,writes,documents,bytes FROM keys WHERE id!='owner' ORDER BY created DESC").fetchall()
        return [{**dict(row), "scopes": json.loads(row["scopes"])} for row in rows]

    def revoke(self, id: str) -> None:
        if id == "owner":
            raise AccessError("Use confirmed recovery to rotate the owner credential", 400)
        with self.transaction() as db:
            db.execute("UPDATE keys SET revoked=1 WHERE id=?", (id,))
            self._audit(db, "key_revoked", id)

    def spend(self, id: str, window: str, limit: int, amount: int = 1, field: str = "requests") -> None:
        if field not in {"requests", "documents", "bytes"}:
            raise ValueError("Invalid quota field")
        with self.transaction() as db:
            db.execute("DELETE FROM usage WHERE window NOT LIKE ? AND window NOT LIKE ?", (time.strftime("%Y-%m-%d", time.gmtime()) + "%", str(int(time.time() // 3600)) + "%"))
            self._spend(db, id, window, limit, amount, field)

    def _spend(self, db, id, window, limit, amount=1, field="requests") -> None:
        db.execute("INSERT OR IGNORE INTO usage(id,window) VALUES (?,?)", (id, window))
        used = db.execute(f"SELECT {field} FROM usage WHERE id=? AND window=?", (id, window)).fetchone()[0]
        if used + amount > limit:
            period = 86400 if len(window) == 10 and window[4] == "-" else 60 if ":minute:" in window or ":write:" in window else 3600
            retry = max(1, math.ceil(period - time.time() % period))
            label = {"documents": "Daily document quota", "bytes": "Daily byte quota", "requests": "Request rate limit"}[field]
            raise AccessError(label + " exceeded; retry later", 429, retry)
        db.execute(f"UPDATE usage SET {field}={field}+? WHERE id=? AND window=?", (amount, id, window))

    def rate(self, principal: Principal, cost: int = 1) -> None:
        self.spend(principal.id, str(int(time.time() // 3600)) + ":minute:" + str(int(time.time() // 60)), principal.rpm, cost)

    def submission_quota(self, db, principal: Principal, size: int) -> None:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        self._spend(db, principal.id, day, principal.documents, field="documents")
        self._spend(db, principal.id, day, principal.bytes, size, field="bytes")
        self._spend(db, principal.id, str(int(time.time() // 3600)) + ":write:" + str(int(time.time() // 60)), principal.writes)

    def challenge(self, purpose: str, payload: dict) -> str:
        code = "bfr_" + secrets.token_urlsafe(32)
        with self.transaction() as db:
            db.execute("DELETE FROM challenges WHERE expires<?", (time.time(),))
            db.execute("INSERT INTO challenges VALUES (?,?,?,?,0)", (digest(code), purpose, json.dumps(payload), time.time() + self.limits["recovery_seconds"]))
        return code

    def cancel_challenge(self, code: str) -> None:
        with self.transaction() as db:
            db.execute("UPDATE challenges SET used=1 WHERE hash=?", (digest(code),))

    def confirm(self, code: str, purpose: str) -> dict:
        with self.transaction() as db:
            row = db.execute("SELECT * FROM challenges WHERE hash=?", (digest(code),)).fetchone()
            if not row or row["used"] or row["expires"] <= time.time() or row["purpose"] != purpose:
                raise AccessError("Invalid, expired or already-used confirmation code", 400)
            db.execute("UPDATE challenges SET used=1 WHERE hash=?", (digest(code),))
            payload = json.loads(row["payload"])
            if purpose == "email":
                self._set(db, "email", payload["email"])
                self._set(db, "email_verified", True)
                db.execute("UPDATE challenges SET used=1 WHERE purpose IN ('email','recovery')")
                self._audit(db, "email_verified", "owner")
                return {"email": payload["email"], "verified": True}
            if purpose == "recovery":
                current = db.execute("SELECT value FROM meta WHERE name='email'").fetchone()
                verified = db.execute("SELECT value FROM meta WHERE name='email_verified'").fetchone()
                if not verified or not json.loads(verified[0]) or not current or payload.get("email") != json.loads(current[0]):
                    raise AccessError("Recovery email changed; request a new code", 400)
                db.execute("UPDATE challenges SET used=1 WHERE purpose='recovery'")
                return {"token": self._rotate_owner(db)}
            raise AccessError("Unsupported confirmation purpose", 400)
