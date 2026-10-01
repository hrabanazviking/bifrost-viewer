"""Provider contract and failure-state tests; doubles are not CUDA evidence."""
import json
import os
from pathlib import Path
import threading

import httpx
import pytest

from inference import ChatRouter, InferenceUnavailable, Provider, load_policy, private_key


def router(handler, *, fallback=False):
    policy = load_policy(Path(__file__).parents[1] / "inference.json")
    value = ChatRouter(Provider("aesir", "http://127.0.0.1:18434", "llama3.2:3b", "x" * 32), policy,
                       Provider("ollama", "http://localhost:11434", "llama3.2:3b") if fallback else None)
    value.client.close()
    value.client = httpx.Client(transport=httpx.MockTransport(handler))
    return value


def result(**extra):
    return {"text": "Four", "finish_reason": "eos", "backend": "cuda", "model": "llama3.2:3b", **extra}


def test_native_request_and_embedding_separation():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=result())
    with_router = router(handler)
    try:
        assert with_router.chat("two plus two", system="concise", max_tokens=16) == "Four"
        assert calls[0].url.path == "/v1/generate"
        assert calls[0].headers["authorization"] == "Bearer " + "x" * 32
        assert json.loads(calls[0].content) == {"prompt": "two plus two", "system": "concise", "max_tokens": 16, "timeout_ms": 45000, "temperature": 0}
        assert with_router.snapshot()["last_provider"] == "aesir"
    finally:
        with_router.close()


@pytest.mark.parametrize("payload", [result(finish_reason="timeout"), result(text=""), result(model="other"), result(backend="cpu"), []])
def test_incomplete_or_wrong_model_never_becomes_success(payload):
    value = router(lambda _: httpx.Response(200, json=payload))
    try:
        with pytest.raises(InferenceUnavailable):
            value.chat("test")
    finally:
        value.close()


def test_circuit_skips_outage_and_recovers_after_cooldown(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("inference.time.monotonic", lambda: clock[0])
    calls, healthy = [], [False]
    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/api/chat":
            assert "authorization" not in request.headers
            return httpx.Response(200, json={"done": True, "model": "llama3.2:3b", "done_reason": "stop", "message": {"content": "Fallback"}})
        return httpx.Response(200, json=result()) if healthy[0] else httpx.Response(503)
    value = router(handler, fallback=True)
    try:
        assert value.chat("x") == value.chat("x") == value.chat("x") == "Fallback"
        assert calls.count("/v1/generate") == 2
        assert value.snapshot()["circuit"] == "open"
        clock[0] += 31
        healthy[0] = True
        assert value.chat("x") == "Four"
        assert value.snapshot()["circuit"] == "closed"
    finally:
        value.close()


@pytest.mark.parametrize("status", [400, 401, 403, 422])
def test_rejected_input_does_not_fallback_or_poison_circuit(status):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(status, json={"error": "private details"})
    value = router(handler, fallback=True)
    try:
        for _ in range(3):
            with pytest.raises(InferenceUnavailable, match="rejected") as exc:
                value.chat("x")
            assert "private" not in str(exc.value)
        assert calls == ["/v1/generate"] * 3
        assert value.snapshot()["circuit"] == "closed"
    finally:
        value.close()


def test_concurrent_calls_are_bounded_and_slots_recover():
    started, release = threading.Event(), threading.Event()
    def handler(_):
        started.set()
        assert release.wait(5)
        return httpx.Response(200, json=result())
    value = router(handler)
    answers = []
    thread = threading.Thread(target=lambda: answers.append(value.chat("x")))
    try:
        thread.start()
        assert started.wait(5)
        with pytest.raises(InferenceUnavailable, match="busy"):
            value.chat("x")
        release.set()
        thread.join(5)
        assert answers == ["Four"] and not thread.is_alive()
        assert value.chat("again") == "Four"
    finally:
        release.set()
        thread.join(5)
        value.close()


def test_private_key_rejects_public_symlink_fifo_and_oversized(tmp_path):
    key = tmp_path / "key"
    key.write_text("x" * 32 + "\n")
    key.chmod(0o600)
    assert private_key(key) == "x" * 32
    link = tmp_path / "link"
    link.symlink_to(key)
    with pytest.raises(OSError):
        private_key(link)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo, 0o600)
    with pytest.raises(ValueError):
        private_key(fifo)
    key.chmod(0o644)
    with pytest.raises(ValueError):
        private_key(key)
    key.chmod(0o600)
    key.write_text("x" * 258)
    with pytest.raises(ValueError):
        private_key(key)


def test_health_is_cached_and_reports_model_mismatch():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"status": "ready", "model": "other", "capabilities": {"text_generation": True}})
    value = router(handler)
    try:
        assert not value.health()["ready"]
        assert not value.health()["ready"]
        assert calls == ["/health"]
    finally:
        value.close()


def test_response_size_redirect_and_policy_fail_closed(tmp_path):
    for response in [httpx.Response(302, headers={"location": "http://attacker.invalid"}),
                     httpx.Response(200, content=b"x" * 1048577)]:
        value = router(lambda _: response)
        try:
            with pytest.raises(InferenceUnavailable):
                value.chat("x")
        finally:
            value.close()
    policy = load_policy(Path(__file__).parents[1] / "inference.json")
    policy["concurrency"] = 0
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy))
    with pytest.raises(ValueError):
        load_policy(path)


def test_aesir_refuses_remote_and_credential_bearing_origins():
    for url in ("http://192.168.1.2:18434", "http://token@127.0.0.1:18434", "http://127.0.0.1:18434/path"):
        with pytest.raises(ValueError):
            Provider("aesir", url, "model", "x" * 32)


@pytest.mark.parametrize("override", [{"model": "wrong"}, {"done": False}, {"done_reason": "timeout"}])
def test_fallback_rejects_wrong_model_and_partial_answers(override):
    def handler(request):
        if request.url.path == "/v1/generate":
            return httpx.Response(503)
        return httpx.Response(200, json={"done": True, "model": "llama3.2:3b",
            "done_reason": "stop", "message": {"content": "partial"}, **override})
    value = router(handler, fallback=True)
    try:
        with pytest.raises(InferenceUnavailable, match="fallback"):
            value.chat("x")
    finally:
        value.close()


@pytest.mark.parametrize("models,ready", [([], False), ([{"name": "other"}], False),
    ([{"name": "llama3.2:3b"}], True)])
def test_ollama_health_requires_the_configured_model(models, ready):
    value = router(lambda _: httpx.Response(200, json={"models": models}))
    value.primary = Provider("ollama", "http://localhost:11434", "llama3.2:3b")
    try:
        assert value.health()["ready"] is ready
    finally:
        value.close()
