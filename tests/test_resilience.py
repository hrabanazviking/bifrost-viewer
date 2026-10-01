"""Recovery tests use isolated cache paths; the production corpus is untouched."""
import asyncio
import subprocess
from types import SimpleNamespace

import numpy as np
import orjson
import pytest

import viewer
from runtime_support import atomic_json
from scripts.watch_inbox import InboxWorker, read_urls


@pytest.fixture
def isolated_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(viewer, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(viewer, "LOG_DIR", tmp_path)
    monkeypatch.setattr(viewer, "fingerprint", lambda: "v2_test")
    monkeypatch.setattr(viewer, "_build_proc", {"proc": None, "fp": None})
    monkeypatch.setattr(viewer, "_cache_validity", {})
    return tmp_path


def test_failed_atomic_write_keeps_last_good_file(monkeypatch, tmp_path):
    path = tmp_path / "cache.json"
    atomic_json(path, {"original": True})
    with pytest.raises(TypeError):
        atomic_json(path, {"bad": object()})
    assert orjson.loads(path.read_bytes()) == {"original": True}


def test_builder_repairs_wrong_shape_status(monkeypatch, tmp_path):
    import graph_builder
    monkeypatch.setattr(graph_builder, "CACHE_DIR", tmp_path)
    graph_builder.status_path("test").write_text("[]")
    graph_builder.write_status("test", stage="queued", running=True)
    assert orjson.loads(graph_builder.status_path("test").read_bytes())["stage"] == "queued"


def test_entity_layout_watchdog_stops_stalled_child(monkeypatch, isolated_cache):
    calls = []
    proc = SimpleNamespace(poll=lambda: None, kill=lambda: calls.append("killed"), wait=lambda timeout: None)
    monkeypatch.setattr(viewer, "_entity_proc", {"proc": proc, "fp": "test", "started_at": 0})
    monkeypatch.setattr(viewer, "BUILD_STALL_AFTER_SEC", 1)
    viewer._check_entity_layout()
    assert calls == ["killed"]
    assert viewer._read_build_status("entity_test")["stage"] == "stalled"


def test_corrupt_existing_cache_can_rebuild(monkeypatch, isolated_cache):
    viewer.cache_path("v2_test").write_bytes(b"broken json")
    proc = SimpleNamespace(pid=123, poll=lambda: None)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: proc)
    assert viewer.load_cached_graph() is None
    assert viewer.kick_off_build() is True
    assert orjson.loads(viewer._build_status_path("v2_test").read_bytes())["stage"] == "queued"


def test_crashed_build_is_persisted_and_retried(monkeypatch, isolated_cache):
    viewer._build_proc.update(proc=SimpleNamespace(poll=lambda: 1), fp="v2_test", retry_after=0)
    atomic_json(viewer._build_status_path("v2_test"), {"running": True})
    assert viewer._checked_build_status("v2_test")["stage"] == "failed"
    assert not viewer._read_build_status("v2_test")["running"]
    calls = []
    monkeypatch.setattr(viewer, "kick_off_build", lambda: calls.append(True))
    viewer._maintenance_tick()
    assert calls == [True]


def test_startup_survives_unavailable_database(monkeypatch):
    def fail():
        raise ConnectionError("database is unavailable")
    monkeypatch.setattr(viewer, "get_pool", fail)
    monkeypatch.setattr(viewer, "_maintenance_tick", fail)
    monkeypatch.setattr(viewer, "_pool", None)
    async def run():
        async with viewer.lifespan(viewer.app):
            await asyncio.sleep(.03)
    asyncio.run(run())


def test_tiny_corpus_projection_does_not_call_umap():
    assert viewer._project_umap_3d(np.ones((2, 6)), 2).shape == (2, 3)


def test_blocked_chunk_edges_match_dense_reference(monkeypatch):
    monkeypatch.setattr(viewer, "EDGE_BLOCK_SIZE", 3)
    monkeypatch.setattr(viewer, "EDGE_TOP_K", 4)
    monkeypatch.setattr(viewer, "EDGE_MIN_SIM", .1)
    vectors = np.random.default_rng(8).normal(size=(17, 6)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    sim = vectors @ vectors.T
    np.fill_diagonal(sim, -1)
    expected = set()
    for i, neighbors in enumerate(np.argpartition(-sim, kth=3, axis=1)[:, :4]):
        for j in neighbors:
            if sim[i, j] >= .1:
                expected.add(tuple(sorted((i, int(j)))))
    actual = viewer._build_top_k_edges(vectors, list(range(17)), [set()] * 17, 17)
    assert {(edge["source"], edge["target"]) for edge in actual} == expected


def test_inbox_retry_survives_worker_restart(monkeypatch, tmp_path):
    worker = InboxWorker(tmp_path)
    worker.settle = 0
    worker.retry_base = 0
    path = worker.inbox / "note.md"
    path.write_text("safe test document")
    monkeypatch.setattr(worker, "run_ingest", lambda target: (_ for _ in ()).throw(ConnectionError("offline")))
    worker.process(path)
    assert (worker.failed / "note.md").exists()
    restarted = InboxWorker(tmp_path)
    restarted.settle = 0
    calls = []
    monkeypatch.setattr(restarted, "run_ingest", calls.append)
    restarted.scan()
    assert len(calls) == 1
    assert (worker.processed / "note.md").exists()


def test_partial_url_retry_skips_already_completed_urls(monkeypatch, tmp_path):
    worker = InboxWorker(tmp_path)
    worker.settle = worker.retry_base = 0
    path = worker.inbox / "batch.urls"
    path.write_text("https://example.org/one\nhttps://example.org/two\n")
    def ingest(target):
        if target.endswith("two"):
            raise ConnectionError("offline")
    monkeypatch.setattr(worker, "run_ingest", ingest)
    worker.process(path)
    restarted = InboxWorker(tmp_path)
    restarted.settle = 0
    calls = []
    monkeypatch.setattr(restarted, "run_ingest", calls.append)
    restarted.scan()
    assert calls == ["https://example.org/two"]


def test_archive_does_not_overwrite_previous_input(tmp_path):
    worker = InboxWorker(tmp_path)
    original = worker.processed / "note.md"
    original.write_text("old")
    incoming = worker.inbox / "note.md"
    incoming.write_text("new")
    destination = worker.archive(incoming, worker.processed)
    assert destination != original
    assert original.read_text() == "old"
    assert destination.read_text() == "new"


def test_normal_text_file_is_not_misread_as_url_batch(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("https://example.org\nthis is a note\n")
    assert read_urls(path) is None


def test_watcher_uses_source_directory_and_separate_durable_state(monkeypatch, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    state = tmp_path / "private-state"
    worker = InboxWorker(source, state_dir=state)
    calls = []
    monkeypatch.setattr("scripts.watch_inbox.run_child", lambda command, cwd, timeout, stop, **kwargs: calls.append((command, cwd)))
    worker.run_ingest("test.md")
    assert worker.inbox == state / "inbox"
    assert calls[0][0][1] == str(source / "ingest.py")
    assert calls[0][1] == source


def test_viewer_queue_uses_bundled_ingest_and_restricted_configuration(tmp_path, monkeypatch):
    from security.queue import IngestQueue
    from security import sandbox
    monkeypatch.setattr(sandbox, "available", lambda: "/usr/bin/bwrap")
    store = viewer.get_security()
    env = tmp_path / "api.env"
    queue = IngestQueue(store, tmp_path / "ingest", env)
    command, environment = queue._command({"id": "fixed", "principal": "test-client", "kind": "url", "payload": '{"url":"https://example.org/test"}'})
    assert command[-4:] == [str(tmp_path / "ingest/.venv/bin/python"), str(tmp_path / "ingest/ingest.py"), "add", "https://example.org/test"]
    assert environment["INGEST_ENV_FILE"] == "/worker.env"
    assert "INGEST_DB_URL" not in environment


def test_malformed_explicit_url_batch_is_retained(monkeypatch, tmp_path):
    worker = InboxWorker(tmp_path)
    worker.settle = 0
    path = worker.inbox / "batch.urls"
    path.write_text("https://example.org/valid\ninvalid URL\n")
    calls = []
    monkeypatch.setattr(worker, "run_ingest", calls.append)
    worker.process(path)
    assert calls == []
    assert (worker.failed / path.name).exists()


def test_search_falls_back_to_keyword_matches(monkeypatch):
    monkeypatch.setattr(viewer, "ollama_embed", lambda texts: (_ for _ in ()).throw(ConnectionError("offline")))
    monkeypatch.setattr(viewer, "_keyword_hits", lambda query, k: [{"id": 42, "doc_id": 7, "sim": 0, "score": .3}])
    response = viewer.search("rainbow", k=3)
    payload = orjson.loads(response.body)
    assert payload["degraded"] is True
    assert payload["search_mode"] == "keyword"
    assert payload["hits"][0]["doc_id"] == 7


def test_empty_document_graph_is_valid():
    result = viewer._build_document_payload("empty", [], np.empty((0, 3)), np.empty((0, 4)), {}, {})
    assert result["nodes"] == []
    assert result["links"] == []


def test_document_graph_is_sparse(monkeypatch):
    monkeypatch.setattr(viewer, "EDGE_TOP_K", 2)
    ids = list(range(10))
    vectors = np.ones((10, 4), dtype=np.float32) / 2
    payload = viewer._build_document_payload("test", ids, np.zeros((10, 3)), vectors,
                                             {i: ("title", "md", "source") for i in ids}, {i: "#fff" for i in ids})
    assert len(payload["links"]) <= 20
    assert payload["stats"]["edge_top_k"] == 2
