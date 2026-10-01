"""Failure-oriented tests for credential recovery and delegated admission."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import viewer
from ingest import safe_fetch
from security import routes
from security.gateway import SecurityGateway
from security.queue import IngestQueue
from security.store import AccessError, SecurityStore, digest
from security import mail, sandbox


@pytest.fixture
def store(tmp_path):
    store = SecurityStore(tmp_path / "private", "old-token", "owner@example.com")
    store.set_setting("email_verified", True)
    return store


@pytest.fixture
def queue(store, tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "available", lambda: "/usr/bin/bwrap")
    project = tmp_path / "ingest"
    (project / ".venv/bin").mkdir(parents=True)
    (project / ".venv/bin/python").touch()
    env = tmp_path / "append.env"
    env.touch()
    return IngestQueue(store, project, env)


def principal(store, **kwargs):
    data = store.create_key("test AI", ["read", "ingest"], 30, **kwargs)
    return store.authenticate(data["token"])


def test_bootstrap_legacy_read_only_and_persistence(store):
    assert store.authenticate("old-token").scopes == {"read"}
    token = store.owner_token()
    assert store.authenticate(token).scopes == {"read", "ingest", "admin"}
    restarted = SecurityStore(store.directory, "different-old-token")
    assert restarted.owner_token() == token
    assert store.path.stat().st_mode & 0o777 == 0o600
    assert store.directory.stat().st_mode & 0o777 == 0o700


def test_keys_expiry_revocation_and_no_plaintext_listing(store):
    key = store.create_key("Reader", ["read"], 1)
    assert key["token"] not in json.dumps(store.list_keys())
    with store.transaction() as db:
        db.execute("UPDATE keys SET expires=0.1 WHERE id=?", (key["id"],))
    with pytest.raises(AccessError):
        store.authenticate(key["token"])
    key = store.create_key("Writer", ["read", "ingest"], 1)
    store.revoke(key["id"])
    with pytest.raises(AccessError):
        store.authenticate(key["token"])
    with pytest.raises(AccessError):
        store.create_key("Admin", ["admin"], 1)


def test_recovery_single_use_rotates_only_after_confirmation(store):
    old = store.owner_token()
    code = store.challenge("recovery", {"email": "owner@example.com"})
    other = store.challenge("recovery", {"email": "owner@example.com"})
    assert store.authenticate(old)
    new = store.confirm(code, "recovery")["token"]
    assert store.authenticate(new)
    with pytest.raises(AccessError):
        store.authenticate(old)
    for replay in (code, other):
        with pytest.raises(AccessError):
            store.confirm(replay, "recovery")


def test_expired_code_and_failed_mail_keep_access_and_email(store, monkeypatch):
    old = store.owner_token()
    code = store.challenge("recovery", {"email": "owner@example.com"})
    with store.transaction() as db:
        db.execute("UPDATE challenges SET expires=0 WHERE hash=?", (digest(code),))
    with pytest.raises(AccessError):
        store.confirm(code, "recovery")
    sent = []
    def fail(store, address, code, purpose):
        sent.append(code)
        raise ConnectionError("SMTP unavailable")
    monkeypatch.setattr(routes, "send_code", fail)
    with pytest.raises(AccessError):
        routes.deliver(store, "new@example.com", "email")
    assert store.authenticate(old) and store.setting("email") == "owner@example.com"
    with pytest.raises(AccessError):
        store.confirm(sent[0], "email")


def test_email_change_requires_confirmation_and_cancels_old_recovery(store):
    recovery = store.challenge("recovery", {"email": "owner@example.com"})
    code = store.challenge("email", {"email": "new@example.com"})
    assert store.setting("email") == "owner@example.com"
    assert store.confirm(code, "email") == {"email": "new@example.com", "verified": True}
    with pytest.raises(AccessError):
        store.confirm(recovery, "recovery")


def test_queue_idempotency_conflict_and_atomic_quota(queue, store):
    client = principal(store, bytes=100)
    payload = {"title": "sample", "text": "bounded data"}
    job = queue.submit(client, "text", payload, "stable")
    assert queue.submit(client, "text", payload, "stable")["job_id"] == job["job_id"]
    with pytest.raises(AccessError) as exc:
        queue.submit(client, "text", {"text": "other"}, "stable")
    assert exc.value.status == 409
    with pytest.raises(AccessError):
        queue.submit(client, "text", {"text": "a" * 101}, None)
    with store.transaction() as db:
        assert db.execute("SELECT SUM(documents) FROM usage WHERE id=?", (client.id,)).fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1


def test_queue_capacity_and_restart_and_owner_isolation(queue, store):
    client = principal(store)
    store.limits["key_pending_jobs"] = 1
    job = queue.submit(client, "text", {"text": "a"}, None)
    with pytest.raises(AccessError) as exc:
        queue.submit(client, "text", {"text": "b"}, None)
    assert exc.value.status == 429
    with store.transaction() as db:
        db.execute("UPDATE jobs SET status='running'")
    restarted = IngestQueue(store, queue.project, queue.env_file)
    assert restarted.states(client, job["job_id"])[0]["status"] == "queued"
    assert isinstance(restarted.states(client, job["job_id"])[0]["started_at"], str)
    assert restarted.states(principal(store), job["job_id"]) == []


def test_revoked_queued_job_never_starts_process(queue, store, monkeypatch):
    client = principal(store)
    job = queue.submit(client, "text", {"text": "a"}, None)
    store.revoke(client.id)
    monkeypatch.setattr(queue, "_command", lambda job: pytest.fail("revoked job launched"))
    queue._execute(queue._claim())
    assert queue.states(client, job["job_id"])[0]["status"] == "failed"


def test_worker_deadline_kills_and_bounds_retries(queue, store, monkeypatch):
    import subprocess
    client = principal(store)
    job = queue.submit(client, "text", {"text": "a"}, None)
    calls = []
    def wait(timeout):
        if not calls:
            raise subprocess.TimeoutExpired("worker", timeout)
        return -9
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: SimpleNamespace(wait=wait))
    monkeypatch.setattr(queue, "_kill", lambda: calls.append("killed"))
    queue._execute(queue._claim())
    assert calls == ["killed"]
    assert queue.states(client, job["job_id"])[0]["status"] == "queued"


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "100.67.240.22", "169.254.169.254", "::1", "::ffff:127.0.0.1", "192.0.2.1"])
def test_url_rejects_internal_reserved_and_mapped_addresses(monkeypatch, address):
    monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", lambda *args, **kwargs: [(0, 0, 0, "", (address, 80))])
    with pytest.raises(ValueError):
        safe_fetch.destination("http://example.com")


def test_mixed_dns_and_redirect_to_local_rejected(monkeypatch):
    def dns(host, *args, **kwargs):
        addresses = ["93.184.215.14"] if host == "public.example" else ["93.184.215.14", "127.0.0.1"]
        return [(0, 0, 0, "", (ip, 80)) for ip in addresses]
    monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", dns)
    response = SimpleNamespace(status=302, getheader=lambda name: "http://private.example")
    connections = []
    class Connection:
        def __init__(self, *args): connections.append(args)
        def request(self, *args, **kwargs): pass
        def getresponse(self): return response
        def close(self): pass
    monkeypatch.setattr(safe_fetch, "PinnedHTTP", Connection)
    with pytest.raises(ValueError):
        safe_fetch.fetch_public("http://public.example")
    assert len(connections) == 1 and connections[0][1] == ["93.184.215.14"]


def test_api_scopes_body_origin_host_and_secret_redaction(monkeypatch):
    store = viewer.get_security()
    token = store.owner_token()
    headers = {"Authorization": "Bearer " + token}
    with TestClient(viewer.app, base_url="http://localhost") as client:
        assert client.post("/api/admin/mail", headers={"Authorization": "Bearer test-token"}, json={}).status_code == 403
        assert client.post("/api/admin/mail", headers=headers, content=b"x" * (store.limits["body_bytes"] + 1)).status_code == 413
        assert client.get("/api/auth/me", headers={**headers, "Origin": "https://hostile.example"}).status_code == 403
        assert client.get("/api/auth/me", headers={**headers, "Host": "hostile.example"}).status_code == 400
        cfg = {"host": "smtp.example.com", "port": 587, "mode": "starttls", "username": "owner@example.com", "sender": "owner@example.com", "password": "private-app-password"}
        assert client.post("/api/admin/mail", headers=headers, json=cfg).status_code == 200
        data = client.get("/api/admin/settings", headers=headers)
        assert "private-app-password" not in data.text and "password" not in data.json()["mail"]
        assert data.headers["referrer-policy"] == "no-referrer"
        cfg["password"] = "sensitive" * 120
        failure = client.post("/api/admin/mail", headers=headers, json=cfg)
        assert failure.status_code == 422 and cfg["password"] not in failure.text


def test_transport_does_not_trust_forwarded_header(store):
    async def app(scope, receive, send):
        pytest.fail("Cleartext public request reached application")
    middleware = SecurityGateway(app, lambda: store, "127.0.0.1")
    scope = {"type": "http", "scheme": "http", "client": ("8.8.8.8", 1000), "method": "GET", "path": "/api/auth/me", "headers": [(b"host", b"localhost"), (b"x-forwarded-proto", b"https")]}
    messages = []
    async def send(message): messages.append(message)
    asyncio.run(middleware(scope, None, send))
    assert messages[0]["status"] == 403


def test_rate_returns_retry_after():
    store = viewer.get_security()
    key = store.create_key("Tiny limit", ["read"], 1, rpm=1)
    with TestClient(viewer.app, base_url="http://localhost") as client:
        headers = {"Authorization": "Bearer " + key["token"]}
        assert client.get("/api/auth/me", headers=headers).status_code == 200
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 429 and 1 <= int(response.headers["retry-after"]) <= 60


def test_recovery_request_generic_and_bounded(monkeypatch):
    store = viewer.get_security()
    store.set_setting("email", "owner@example.com")
    store.set_setting("email_verified", True)
    sent = []
    monkeypatch.setattr(routes, "send_code", lambda store, address, code, purpose: sent.append((address, code)))
    with TestClient(viewer.app, base_url="http://localhost") as client:
        yes = client.post("/api/auth/recovery/request", json={"email": "owner@example.com"})
        no = client.post("/api/auth/recovery/request", json={"email": "unknown@example.com"})
        assert yes.status_code == no.status_code == 202 and yes.json() == no.json()
        assert len(sent) == 1
        old = store.owner_token()
        new = client.post("/api/auth/recovery/confirm", json={"code": sent[0][1]}).json()["token"]
        assert store.authenticate(new)
        with pytest.raises(AccessError):
            store.authenticate(old)


def test_mail_refuses_login_when_tls_negotiation_fails(store, monkeypatch):
    store.set_setting("mail", {"host": "smtp.example.com", "port": 587, "mode": "starttls", "sender": "owner@example.com", "username": "owner@example.com", "password": "test-app-password"})
    calls = []
    class SMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def ehlo(self): calls.append("hello")
        def starttls(self, context): raise ConnectionError("TLS handshake failed")
        def login(self, *args): pytest.fail("Credentials transmitted without TLS")
    monkeypatch.setattr(mail.smtplib, "SMTP", SMTP)
    with pytest.raises(ConnectionError):
        mail.send_code(store, "owner@example.com", "code", "recovery")
    assert calls == ["hello"]


def test_recovery_code_for_previous_email_cannot_rotate_owner(store):
    code = store.challenge("email", {"email": "new@example.com"})
    store.confirm(code, "email")
    stale = store.challenge("recovery", {"email": "owner@example.com"})
    owner = store.owner_token()
    with pytest.raises(AccessError):
        store.confirm(stale, "recovery")
    assert store.authenticate(owner)


def test_compressed_and_oversized_url_responses_rejected(monkeypatch):
    monkeypatch.setattr(safe_fetch, "destination", lambda url: ("https", "public.example", 443, ["93.184.215.14"]))
    class Connection:
        encoding = "gzip"
        def __init__(self, *args): pass
        def request(self, *args, **kwargs): pass
        def close(self): pass
        def getresponse(self): return self
        status = 200
        def getheader(self, name, default=None): return self.encoding
        def read(self, size): return b"a" * size
    monkeypatch.setattr(safe_fetch, "PinnedHTTP", Connection)
    with pytest.raises(ValueError, match="Compressed"):
        safe_fetch.fetch_public("https://public.example")
    Connection.encoding = "identity"
    with pytest.raises(ValueError, match="limit"):
        safe_fetch.fetch_public("https://public.example")


def test_chunked_body_cannot_bypass_body_limit(store):
    async def app(scope, receive, send):
        pytest.fail("Oversized chunked body reached application")
    store.limits["body_bytes"] = 4
    middleware = SecurityGateway(app, lambda: store, "127.0.0.1")
    scope = {"type": "http", "scheme": "http", "client": ("127.0.0.1", 1000), "method": "POST", "path": "/api/auth/recovery/request", "headers": [(b"host", b"localhost")]}
    responses, chunks = [], iter([b"aaa", b"bbb"])
    async def send(message): responses.append(message)
    async def receive(): return {"type": "http.request", "body": next(chunks), "more_body": True}
    asyncio.run(middleware(scope, receive, send))
    assert responses[0]["status"] == 413


def test_request_body_timeout_fails_closed(store):
    async def app(scope, receive, send):
        pytest.fail("Incomplete body reached application")
    store.limits["body_timeout_seconds"] = .01
    middleware = SecurityGateway(app, lambda: store, "127.0.0.1")
    scope = {"type": "http", "scheme": "http", "client": ("127.0.0.1", 1000), "method": "POST", "path": "/api/auth/recovery/request", "headers": [(b"host", b"localhost")]}
    responses = []
    async def send(message): responses.append(message)
    async def receive(): await asyncio.sleep(.1)
    asyncio.run(middleware(scope, receive, send))
    assert responses[0]["status"] == 408


def test_store_failure_requeues_worker_instead_of_stranding_job(queue, store, monkeypatch):
    import sqlite3
    client = principal(store)
    job = queue.submit(client, "text", {"text": "a"}, None)
    monkeypatch.setattr(queue, "_active", lambda id: (_ for _ in ()).throw(sqlite3.OperationalError("temporarily busy")))
    queue._execute(queue._claim())
    assert queue.states(client, job["job_id"])[0]["status"] == "queued"


def test_queue_enforces_retained_job_and_log_budgets(queue, store):
    client = principal(store)
    store.limits["retained_jobs"] = 1
    job = queue.submit(client, "text", {"text": "a"}, None)
    with pytest.raises(AccessError, match="Retained job"):
        queue.submit(client, "text", {"text": "b"}, None)
    store.limits["worker_total_log_bytes"] = 1
    (store.directory / "test.log").write_bytes(b"x")
    queue._execute(queue._claim())
    assert queue.states(client, job["job_id"])[0]["status"] == "failed"


def test_worker_does_not_inherit_owner_environment(queue, store, monkeypatch):
    monkeypatch.setenv("VIEWER_DB_URL", "postgresql://owner:private-password@localhost/db")
    monkeypatch.setenv("GITHUB_TOKEN", "private-git-key")
    client = principal(store)
    queue.submit(client, "text", {"text": "data"}, None)
    command, env = queue._command(queue._claim())
    assert "private-password" not in json.dumps(env) and "private-git-key" not in json.dumps(env)
    assert "--unshare-user" in command and "--disable-userns" in command
    assert str(store.path) not in command
    assert not any(value.endswith("/ingest-viewer/.env") for value in command)
    assert "--ro-bind" in command and env["INGEST_ENV_FILE"] == "/worker.env"


def test_missing_sandbox_fails_closed(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    with pytest.raises(AccessError) as exc:
        sandbox.available()
    assert exc.value.status == 503


def test_web_connection_tries_next_validated_address(monkeypatch):
    calls, socket = [], SimpleNamespace(close=lambda: None)
    def connect(address, timeout):
        calls.append(address)
        if len(calls) == 1:
            raise OSError("Unreachable IPv6 route")
        return socket
    monkeypatch.setattr(safe_fetch.socket, "create_connection", connect)
    connection = safe_fetch.PinnedHTTP("public.example", ["2606:4700::1111", "1.1.1.1"], 80, 1)
    connection.connect()
    assert connection.sock is socket and calls == [("2606:4700::1111", 80), ("1.1.1.1", 80)]


def test_launcher_waits_for_first_owner_bootstrap(monkeypatch, tmp_path):
    from scripts import open_brain
    state = tmp_path / "cold-security"
    monkeypatch.setenv("VIEWER_SECURITY_DIR", str(state))
    monkeypatch.setenv("VIEWER_TOKEN", "")
    monkeypatch.setattr(open_brain, "__file__", str(tmp_path / "scripts/open_brain.py"))
    (tmp_path / ".env").write_text("VIEWER_PORT=8731\nVIEWER_TOKEN=\n")
    monkeypatch.setattr(open_brain.subprocess, "run", lambda *args, **kwargs: None)
    def ready(*args, **kwargs):
        SecurityStore(state, "")
        return SimpleNamespace(status_code=200)
    monkeypatch.setattr(open_brain.httpx, "get", ready)
    opened = []
    monkeypatch.setattr(open_brain.webbrowser, "open", opened.append)
    open_brain.main()
    assert len(opened) == 1 and "#token=bfo_" in opened[0]


def test_limits_override_is_partial_and_rejects_unknown_settings(monkeypatch, tmp_path):
    from security.store import load_limits
    path = tmp_path / "limits.json"
    monkeypatch.setenv("VIEWER_LIMITS_FILE", str(path))
    path.write_text('{"ai_requests_per_minute": 20}')
    assert load_limits()["ai_requests_per_minute"] == 20
    assert load_limits()["body_bytes"] == 262144
    path.write_text('{"typo": 20}')
    with pytest.raises(ValueError):
        load_limits()


def test_untrusted_global_budget_keeps_owner_administration_available():
    store = viewer.get_security()
    store.limits["global_untrusted_requests_per_minute"] = 1
    key = store.create_key("Shared quota", ["read"], 1)
    with TestClient(viewer.app, base_url="http://localhost") as client:
        headers = {"Authorization": "Bearer " + key["token"]}
        assert client.get("/api/auth/me", headers=headers).status_code == 200
        assert client.get("/api/auth/me", headers=headers).status_code == 429
        assert client.get("/api/admin/settings", headers={"Authorization": "Bearer " + store.owner_token()}).status_code == 200


@pytest.mark.parametrize("payload,status", [({"title": "Valid", "text": "invalid\x00data"}, 400), ({"title": "bad\ntitle", "text": "data"}, 422)])
def test_unrepresentable_inputs_fail_before_worker_admission(payload, status):
    store = viewer.get_security()
    key = store.create_key("Validator", ["read", "ingest"], 1)
    with TestClient(viewer.app, base_url="http://localhost") as client:
        response = client.post("/api/ingest/text", headers={"Authorization": "Bearer " + key["token"]}, json=payload)
        assert response.status_code == status
        assert viewer.get_ingest_queue().states(store.authenticate(key["token"])) == []
