"""Opt-in real sandbox/PG/Ollama checks against a dedicated disposable test DB.

Set BIFROST_TEST_INGEST_ENV to a private append-role dotenv file and
BIFROST_TEST_DB_URL to its owner DSN. The database name must start with
bifrost_recovery_test_. These tests append canaries only to that database.
"""
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg.conninfo import conninfo_to_dict
import pytest

from security.queue import IngestQueue
from security.store import SecurityStore

pytestmark = pytest.mark.skipif(not os.getenv("BIFROST_TEST_INGEST_ENV"), reason="Requires isolated integration database")


def configuration():
    env_file = Path(os.environ["BIFROST_TEST_INGEST_ENV"])
    values = dotenv_values(env_file)
    owner = os.environ["BIFROST_TEST_DB_URL"]
    worker_db = conninfo_to_dict(values["INGEST_DB_URL"])["dbname"]
    owner_db = conninfo_to_dict(owner)["dbname"]
    assert worker_db == owner_db and owner_db.startswith("bifrost_recovery_test_")
    return env_file, owner


def test_real_sandbox_preserves_unicode_and_idempotent_replay(tmp_path):
    env_file, owner = configuration()
    project = Path(__file__).resolve().parents[1] / "ingest"
    store = SecurityStore(tmp_path / "security", "unused", "owner@example.org")
    store.set_setting("email_verified", True)
    key = store.create_key("Integration append client", ["read", "ingest"], 1)
    principal = store.authenticate(key["token"])
    queue = IngestQueue(store, project, env_file)
    text = f"Sigrún · Þórr · Bifröst 🌈\nExact UTF-8 text; canary {uuid4().hex}."
    submitted = queue.submit(principal, "text", {"title": "Unicode recovery canary", "text": text}, "fixed")
    queue._execute(queue._claim())
    state = queue.states(principal, submitted["job_id"])[0]
    assert state["status"] == "ok", (state, (store.directory / (submitted["job_id"] + ".log")).read_text())
    assert state["stage"] == "done" and state["progress"] == 1.
    with psycopg.connect(owner) as conn, conn.cursor() as cur:
        cur.execute("SELECT d.id,d.source,d.title,d.metadata,c.text,vector_dims(c.embedding) FROM documents d JOIN chunks c ON c.document_id=d.id WHERE d.metadata->>'api_job_id'=%s", (submitted["job_id"],))
        rows = cur.fetchall()
        assert len(rows) == 1
        doc_id, source, title, metadata, actual, dimension = rows[0]
        assert actual == text and dimension == 768
        assert source == f"bifrost-api://{principal.id}/{submitted['job_id']}"
        assert title == "Unicode recovery canary"
        assert metadata == {"api_job_id": submitted["job_id"], "api_client_id": principal.id}
    # Simulate the owner losing the success acknowledgement and replaying.
    with store.transaction() as db:
        db.execute("UPDATE jobs SET status='running',next_attempt=0 WHERE id=?", (submitted["job_id"],))
    queue._execute(queue._claim())
    assert queue.states(principal)[0]["status"] == "ok"
    with psycopg.connect(owner) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM chunks WHERE document_id=%s", (doc_id,))
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT count(*) FROM documents WHERE metadata->>'api_job_id'=%s", (submitted["job_id"],))
        assert cur.fetchone()[0] == 1


def test_real_append_role_cannot_delete_or_change_schema():
    env_file, _ = configuration()
    worker = dotenv_values(env_file)["INGEST_DB_URL"]
    for statement in ("DELETE FROM documents WHERE false", "UPDATE chunks SET text='bad' WHERE false", "ALTER TABLE documents ADD COLUMN forbidden_test int"):
        with psycopg.connect(worker) as conn:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
            conn.rollback()


def test_real_jsonl_failure_keeps_database_unchanged(tmp_path):
    env_file, owner = configuration()
    project = Path(__file__).resolve().parents[1] / "ingest"
    source = tmp_path / "broken.jsonl"
    source.write_text('{"text":"valid first record"}\n{"broken":\n')
    with psycopg.connect(owner) as conn:
        before = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
    env = {**os.environ, "INGEST_ENV_FILE": str(env_file)}
    result = subprocess.run([str(project / ".venv/bin/python"), str(project / "ingest.py"), "add", str(source)], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 21, result.stderr
    assert "line 2" in result.stderr
    with psycopg.connect(owner) as conn:
        assert conn.execute("SELECT count(*) FROM documents").fetchone()[0] == before
    assert source.exists()


def test_real_skein_build_lock_excludes_second_builder():
    _, owner = configuration()
    from skein.build_guard import build_lock
    with build_lock(owner):
        with pytest.raises(RuntimeError, match="Another Skein build"):
            with build_lock(owner):
                pytest.fail("second build acquired the lock")
    with build_lock(owner):
        pass  # lock is released after success or failure
