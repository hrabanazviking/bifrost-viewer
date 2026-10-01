"""Queue/inbox failure boundaries, with private temporary state and real children."""
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import viewer
from security import sandbox
from security.job_state import recent_progress
from security.queue import IngestQueue
from security.store import AccessError
from scripts.inbox_child import ChildFailure, run_child
from scripts.inbox_state import exclusive_lock, load_state, save_state
from scripts.watch_inbox import InboxWorker
from tests import test_security as fixtures
from runtime_support import publish_graph

principal, queue, store = fixtures.principal, fixtures.queue, fixtures.store


def test_failed_layout_publication_preserves_old_caches(tmp_path):
    old = tmp_path / "skein_graph_old.json"
    old.write_text('{"last_good":true}')
    with pytest.raises(TypeError):
        publish_graph(tmp_path / "skein_graph_new.json", {"invalid": object()}, "skein_graph_")
    assert old.read_text() == '{"last_good":true}'


def test_successful_layout_publication_reclaims_only_obsolete_layouts(tmp_path):
    old = tmp_path / "skein_graph_old.json"
    old.write_text("{}")
    unrelated = tmp_path / "build_status_old.json"
    unrelated.write_text("{}")
    current = tmp_path / "skein_graph_new.json"
    publish_graph(current, {"nodes": []}, "skein_graph_")
    assert current.exists() and unrelated.exists()
    assert not old.exists()


def test_text_sandbox_mounts_payload_not_log(queue, store, monkeypatch):
    client = principal(store)
    text = "Sigrún, Þórr and Bifröst 🌈\nExact submitted text."
    queue.submit(client, "text", {"text": text, "title": "Unicode"}, None)
    calls = []
    original = sandbox.command
    monkeypatch.setattr(sandbox, "command", lambda *args: calls.append(args) or original(*args))
    job = queue._claim()
    command, environment = queue._command(job)
    assert calls[0][2] == store.directory / (job["id"] + ".txt")
    assert calls[0][2].read_text() == text
    assert command[-1] == "/payload.txt"
    assert "INGEST_PROGRESS_FILE" not in environment


@pytest.mark.parametrize("code,category", [(21, "input"), (22, "configuration"), (20, "dependency")])
def test_exit_categories_control_automatic_retries(queue, store, monkeypatch, code, category):
    client = principal(store)
    submitted = queue.submit(client, "text", {"text": "test"}, "stable")
    monkeypatch.setattr("security.queue.subprocess.Popen", lambda *a, **k: SimpleNamespace(wait=lambda timeout: code))
    queue._execute(queue._claim())
    state = queue.states(client, submitted["job_id"])[0]
    assert state["status"] == ("queued" if code == 20 else "failed")
    assert state["error_category"] == category


def test_owner_retry_preserves_identity_and_caps_total_work(queue, store):
    client = principal(store)
    submitted = queue.submit(client, "text", {"text": "test"}, "stable")
    for index in range(store.limits["owner_job_retries"]):
        with store.transaction() as db:
            db.execute("UPDATE jobs SET status='failed' WHERE id=?", (submitted["job_id"],))
        assert queue.retry(submitted["job_id"])["job_id"] == submitted["job_id"]
        assert queue.states(client)[0]["owner_retries"] == index + 1
    with store.transaction() as db:
        db.execute("UPDATE jobs SET status='failed'")
        assert db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
    with pytest.raises(AccessError, match="budget"):
        queue.retry(submitted["job_id"])
    assert queue.submit(client, "text", {"text": "test"}, "stable")["job_id"] == submitted["job_id"]


def test_owner_retry_cannot_bypass_revocation(queue, store):
    client = principal(store)
    job = queue.submit(client, "text", {"text": "test"}, None)
    with store.transaction() as db:
        db.execute("UPDATE jobs SET status='failed'")
    store.revoke(client.id)
    with pytest.raises(AccessError) as rejected:
        queue.retry(job["job_id"])
    assert rejected.value.status == 403


def test_second_queue_supervisor_is_refused(queue, store, monkeypatch):
    monkeypatch.setattr(queue, "_loop", lambda: queue.stop_event.wait(10))
    second = IngestQueue(store, queue.project, queue.env_file)
    queue.start()
    try:
        with pytest.raises(AccessError, match="Another server"):
            second.start()
    finally:
        queue.stop()
    monkeypatch.setattr(second, "_loop", lambda: second.stop_event.wait(10))
    second.start()
    second.stop()


def test_progress_ignores_malformed_newer_marker_and_private_text(tmp_path):
    path = tmp_path / "job.log"
    path.write_text('BIFROST_PROGRESS {"stage":"embedding","progress":0.5,"updated_at":100,"embedded":4,"secret":"never"}\nBIFROST_PROGRESS broken\n')
    assert recent_progress(path, 99) == {"stage": "embedding", "progress": .5, "embedded": 4}
    assert recent_progress(path, 101) == {}
    path.write_text('BIFROST_PROGRESS {"stage":"embedding","progress":NaN,"updated_at":110}\n')
    assert recent_progress(path) == {}


def test_last_good_inbox_metadata_survives_corruption(tmp_path):
    path = tmp_path / "state.json"
    state = {"failed/batch.urls": {"signature": [1, 2, 3, 4], "completed": ["https://example.org/one"], "attempts": 2}}
    save_state(path, state)
    save_state(path, state)
    path.write_text("broken JSON")
    assert load_state(path) == state
    assert json.loads(path.read_text()) == state
    assert list(tmp_path.glob("state.json.corrupt-*"))


def test_malformed_retry_record_does_not_crash_or_discard_valid_records(tmp_path):
    path = tmp_path / "state.json"
    good = {"signature": [1, 2], "attempts": 1, "completed": []}
    path.write_text(json.dumps({"good": good, "bad": {"signature": "wrong", "attempts": []}}))
    assert load_state(path) == {"good": good}


def test_duplicate_inbox_supervisor_cannot_acquire_lock(tmp_path):
    with exclusive_lock(tmp_path / "lock"):
        with pytest.raises(RuntimeError, match="Another supervisor"):
            with exclusive_lock(tmp_path / "lock"):
                pytest.fail("duplicate ownership")


def test_permanent_input_is_retained_until_changed(monkeypatch, tmp_path):
    worker = InboxWorker(tmp_path)
    worker.settle = worker.retry_base = 0
    path = worker.inbox / "broken.jsonl"
    path.write_text("malformed")
    monkeypatch.setattr(worker, "run_ingest", lambda target: (_ for _ in ()).throw(ChildFailure(21)))
    worker.process(path)
    restarted = InboxWorker(tmp_path)
    restarted.settle = 0
    calls = []
    monkeypatch.setattr(restarted, "run_ingest", calls.append)
    restarted.scan()
    assert calls == []
    retained = restarted.failed / path.name
    assert retained.read_text() == "malformed"
    retained.write_text('{"text":"corrected input"}')
    restarted.scan()
    assert len(calls) == 1
    assert (restarted.processed / path.name).exists()


def test_dependency_backoff_survives_restart_and_stops_flood(monkeypatch, tmp_path):
    worker = InboxWorker(tmp_path)
    worker.settle = 0
    for name in ("one.md", "two.md"):
        (worker.inbox / name).write_text(name)
    calls = []
    def fail(target):
        calls.append(target)
        raise ChildFailure(20)
    monkeypatch.setattr(worker, "run_ingest", fail)
    worker.scan()
    assert len(calls) == 1
    restarted = InboxWorker(tmp_path)
    monkeypatch.setattr(restarted, "run_ingest", calls.append)
    restarted.scan()
    assert len(calls) == 1
    assert restarted.health["stage"] == "dependency-backoff"


def test_shutdown_retains_partial_url_completion(monkeypatch, tmp_path):
    worker = InboxWorker(tmp_path)
    worker.settle = 0
    path = worker.inbox / "batch.urls"
    path.write_text("https://example.org/one\nhttps://example.org/two\n")
    def stop_second(target):
        if target.endswith("two"):
            raise InterruptedError()
    monkeypatch.setattr(worker, "run_ingest", stop_second)
    worker.process(path)
    assert path.exists()
    restarted = InboxWorker(tmp_path)
    restarted.settle = 0
    calls = []
    monkeypatch.setattr(restarted, "run_ingest", calls.append)
    restarted.scan()
    assert calls == ["https://example.org/two"]


def test_child_deadline_terminates_descendants(tmp_path):
    child_pid = tmp_path / "child.pid"
    code = "import subprocess,time; from pathlib import Path; p=subprocess.Popen(['sleep','60']); Path('child.pid').write_text(str(p.pid)); time.sleep(60)"
    started = time.monotonic()
    with pytest.raises(ChildFailure) as failure:
        run_child([sys.executable, "-c", code], tmp_path, .3, threading.Event())
    assert failure.value.code == 124
    assert time.monotonic() - started < 6
    proc = Path("/proc") / child_pid.read_text().strip() / "stat"
    assert not proc.exists() or proc.read_text().split()[2] == "Z"


def test_child_large_output_is_drained_without_deadlock(tmp_path):
    run_child([sys.executable, "-c", "import os; os.write(1,b'x'*4_000_000)"], tmp_path, 5, threading.Event())


def test_owner_diagnostics_and_retry_deny_append_clients(monkeypatch):
    store = viewer.get_security()
    client_key = store.create_key("Append client", ["read", "ingest"], 1)
    with TestClient(viewer.app, base_url="http://127.0.0.1:8731") as client:
        headers = {"Authorization": "Bearer " + client_key["token"]}
        assert client.get("/api/admin/ingest/status", headers=headers).status_code == 403
        assert client.post("/api/admin/ingest/jobs/nope/retry", headers=headers).status_code == 403
        owner = {"Authorization": "Bearer " + store.owner_token()}
        response = client.get("/api/admin/ingest/status", headers=owner)
        assert response.status_code == 200
        assert "reserved_bytes" in response.json()["api_queue"]


def test_skein_generation_changes_for_same_source():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(1, "same"), (2, "same")]
    assert viewer._skein_fingerprint(cursor) != viewer._skein_fingerprint(cursor)


def test_skein_snapshot_checks_generation_before_entity_rows(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (2, "same")
    monkeypatch.setattr(viewer, "db_conn", lambda: connection)
    with pytest.raises(RuntimeError, match="generation changed"):
        viewer._build_skein_graph("v2_build1_same")
    assert "READ ONLY" in cursor.execute.call_args_list[0].args[0]
    assert not any("FROM skein_entities" in call.args[0] for call in cursor.execute.call_args_list)


def test_skein_build_failure_keeps_last_good_layout(monkeypatch, tmp_path):
    monkeypatch.setattr(viewer, "LOG_DIR", tmp_path)
    monkeypatch.setattr(viewer, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(viewer, "_skein_build_proc", {"proc": None})
    cache = tmp_path / "entity_old.json"
    cache.write_text('{"old":true}')
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: (_ for _ in ()).throw(OSError("cannot launch")))
    response = viewer.skein_build()
    assert response.status_code == 500
    assert cache.read_text() == '{"old":true}'
