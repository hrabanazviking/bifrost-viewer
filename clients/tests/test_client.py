import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bifrost_client import BifrostClient, ClientError, retry_delay, validated_base


def test_retry_replays_identical_write_and_honors_delay():
    calls, waits = [], []
    def exchange(*args):
        calls.append(args)
        return (503, {"retry-after": "7"}, b'{}') if len(calls) == 1 else (200, {}, b'{"job_id":"saved"}')
    client = BifrostClient("http://127.0.0.1:8731", "synthetic-key", exchange=exchange, sleep=waits.append)
    assert client.add_text("title", "body", "stable-operation-1")["job_id"] == "saved"
    assert calls[0][2:4] == calls[1][2:4] and waits == [7]


@pytest.mark.parametrize("status", [301, 302, 307, 308, 400, 401, 403, 409, 413, 422, 500])
def test_terminal_failure_never_replayed(status):
    calls = []
    def exchange(*args):
        calls.append(args); return status, {"location": "https://evil.example"}, b'{}'
    client = BifrostClient("https://brain.example.org", "synthetic-key", exchange=exchange, sleep=lambda _: pytest.fail("terminal retry"))
    with pytest.raises(ClientError) as exc:
        client.add_url("https://public.example", "operation-1")
    assert len(calls) == 1 and exc.value.status == status


def test_long_retry_after_and_response_errors_are_bounded():
    client = BifrostClient("http://localhost:8731", "synthetic-key", exchange=lambda *a: (429, {"retry-after": "86400"}, b'{}'), sleep=lambda _: pytest.fail("shortened delay"))
    with pytest.raises(ClientError) as error:
        client.health()
    assert error.value.retry_after == 86400
    client.exchange = lambda *a: (200, {}, b'not json')
    with pytest.raises(ClientError, match="invalid JSON"):
        client.health()


def test_connection_loss_retry_same_key_and_missing_id_refused():
    calls = []
    def exchange(*args):
        calls.append(args)
        if len(calls) < 3: raise TimeoutError()
        return 200, {}, b'{"duplicate":true}'
    client = BifrostClient("http://localhost:8731", "synthetic-key", exchange=exchange, sleep=lambda _: None)
    with pytest.raises(ClientError, match="stable"):
        client.add_text("title", "text", "")
    assert not calls
    assert client.add_text("title", "text", "same-operation")["duplicate"] is True
    assert len(calls) == 3 and all(x[2]["Idempotency-Key"] == "same-operation" for x in calls)


@pytest.mark.parametrize("url", ["http://public.example", "https://u:p@example.com", "https://example.com/path", "https://example.com?token=secret", "https://example.com#secret", "https://example.com:99999", "http://private.ts.net'$()"])
def test_transport_and_credentials_rejected(url):
    with pytest.raises(ClientError): validated_base(url)


def test_owner_key_and_admin_methods_refused():
    with pytest.raises(ClientError, match="Owner"):
        BifrostClient("http://localhost:8731", "bfo_synthetic")
    client = BifrostClient("http://localhost:8731", "synthetic-key")
    with pytest.raises(ClientError): client.request("/api/admin/keys")
    with pytest.raises(ClientError): client.request("/api/refresh", {})
    assert retry_delay("Thu, 01 Oct 2026 10:00:00 GMT", 1790848800) == 0


def test_polling_deadline_does_not_resubmit():
    now, waits = [0], []
    def sleep(seconds): waits.append(seconds); now[0] += seconds
    client = BifrostClient("http://localhost:8731", "synthetic-key", exchange=lambda *a: (200, {}, b'{"status":"running"}'), sleep=sleep, clock=lambda: now[0])
    with pytest.raises(ClientError, match="Polling deadline"):
        client.wait("a" * 32, seconds=20)
    assert waits == [15, 5]


def test_response_byte_and_wall_clock_limits(monkeypatch):
    import bifrost_client
    from types import SimpleNamespace
    monkeypatch.setitem(bifrost_client.POLICY, 'max_response_bytes', 4)
    client = BifrostClient('http://localhost:8731', 'synthetic-key')
    response = SimpleNamespace(read1=lambda size: b'12345')
    with pytest.raises(ClientError, match='safety limit'):
        client._read_response(response, SimpleNamespace(sock=None), 5)
    now = [0]
    client.clock = lambda: now[0]
    def trickle(size):
        now[0] += 3
        return b'x'
    with pytest.raises(TimeoutError, match='deadline'):
        client._read_response(SimpleNamespace(read1=trickle), SimpleNamespace(sock=None), 5)
