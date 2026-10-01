"""Bounded stateless chat routing; corpus embedding identity stays with ingest."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import re
import stat
import threading
import time
from urllib.parse import urlsplit

import httpx

log = logging.getLogger("bifrost.inference")


class InferenceUnavailable(RuntimeError):
    """Safe public failure without provider bodies, paths or credentials."""


def load_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    defaults = json.loads(Path(__file__).with_name("inference.json").read_text())
    if not isinstance(policy, dict) or set(policy) != set(defaults):
        raise ValueError("Invalid inference policy fields")
    for key, value in policy.items():
        if type(value) not in (int, float) or not 0 < value <= 1048576:
            if key != "temperature" or type(value) not in (int, float) or value != 0:
                raise ValueError("Invalid inference policy value")
    for key in ("concurrency", "failure_threshold", "max_response_bytes", "ollama_context"):
        if type(policy[key]) is not int:
            raise ValueError("Inference counts must be integers")
    if (policy["concurrency"] > 4 or policy["failure_threshold"] > 10
            or policy["request_timeout_seconds"] > 120
            or policy["connect_timeout_seconds"] > 10
            or policy["queue_timeout_seconds"] > 2
            or policy["ollama_context"] > 8192):
        raise ValueError("Inference policy exceeds service bounds")
    return policy


def private_key(path: Path) -> str:
    """Pin a current-owner private regular file; refuse symlinks and FIFOs."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 257
                or metadata.st_mode & 0o077
                or hasattr(os, "geteuid") and metadata.st_uid != os.geteuid()):
            raise ValueError("Aesir credential must be a private current-owner regular file")
        raw = stream.read(258)
    key = raw.decode("ascii").removesuffix("\n")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", key):
        raise ValueError("Invalid Aesir credential format")
    return key


@dataclass(frozen=True)
class Provider:
    kind: str
    url: str
    model: str
    key: str = field(default="", repr=False)

    def __post_init__(self):
        parsed = urlsplit(self.url)
        if (self.kind not in ("ollama", "aesir") or parsed.scheme not in ("http", "https")
                or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise ValueError("Invalid chat provider origin")
        if self.kind == "aesir" and (parsed.hostname != "127.0.0.1" or not self.key):
            raise ValueError("Aesir requires authenticated IPv4 loopback")


class ChatRouter:
    """One finite queue and circuit per primary; only configured local fallback."""
    def __init__(self, primary: Provider, policy: dict, fallback: Provider | None = None):
        self.primary, self.policy, self.fallback = primary, policy, fallback
        self.client = httpx.Client(trust_env=False, follow_redirects=False)
        self.slots = threading.BoundedSemaphore(policy["concurrency"])
        self.lock = threading.Lock()
        self.failures = 0
        self.open_until = 0.0
        self.probing = False
        self.last_provider = None
        self.last_error = None
        self.health_at = 0.0
        self.health_value = None

    def close(self):
        self.client.close()

    def _request(self, provider: Provider, route: str, body: dict | None) -> dict:
        headers = {"Authorization": "Bearer " + provider.key} if provider.key else {}
        budget = self.policy["request_timeout_seconds"] if body is not None else 3
        timeout = httpx.Timeout(budget, connect=self.policy["connect_timeout_seconds"])
        started = time.monotonic()
        with self.client.stream("POST" if body is not None else "GET",
                provider.url.rstrip("/") + route, json=body, headers=headers,
                timeout=timeout) as response:
            response.raise_for_status()
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                if len(raw) > self.policy["max_response_bytes"] or time.monotonic() - started > budget:
                    raise InferenceUnavailable("Chat response exceeded its budget")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise InferenceUnavailable("Invalid chat response")
        return payload

    def _generate(self, provider: Provider, prompt: str, system: str | None, max_tokens: int) -> str:
        if provider.kind == "aesir":
            body = {"prompt": prompt, "max_tokens": max_tokens,
                    "timeout_ms": int(self.policy["request_timeout_seconds"] * 1000),
                    "temperature": self.policy["temperature"]}
            if system is not None:
                body["system"] = system
            payload = self._request(provider, "/v1/generate", body)
            if (payload.get("finish_reason") not in ("eos", "length")
                    or payload.get("backend") != "cuda" or payload.get("model") != provider.model):
                raise InferenceUnavailable("Aesir generation was incomplete")
            text = payload.get("text")
        else:
            messages = ([{"role": "system", "content": system}] if system is not None else [])
            messages.append({"role": "user", "content": prompt})
            payload = self._request(provider, "/api/chat", {
                "model": provider.model, "messages": messages, "stream": False,
                "options": {"num_predict": max_tokens, "temperature": self.policy["temperature"],
                            "num_ctx": self.policy["ollama_context"]}})
            if (payload.get("done") is not True or payload.get("model") != provider.model
                    or payload.get("done_reason") not in ("stop", "length")):
                raise InferenceUnavailable("Ollama generation was incomplete")
            message = payload.get("message")
            text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise InferenceUnavailable("Chat returned no usable text")
        return text.strip()

    def _admit_primary(self) -> bool:
        with self.lock:
            if self.open_until:
                if time.monotonic() < self.open_until or self.probing:
                    return False
                self.probing = True
            return True

    def _result(self, succeeded: bool):
        with self.lock:
            if succeeded:
                self.failures = 0
                self.open_until = 0.0
                self.last_error = None
            else:
                self.failures += 1
                self.last_error = "unavailable"
                if self.failures >= self.policy["failure_threshold"]:
                    self.open_until = time.monotonic() + self.policy["cooldown_seconds"]
            self.probing = False
            self.health_at = 0.0

    def chat(self, prompt: str, *, system: str | None = None, max_tokens: int = 256) -> str:
        if (not isinstance(prompt, str) or not prompt or len(prompt.encode()) > 65536
                or system is not None and (not isinstance(system, str) or len(system.encode()) > 65536)
                or type(max_tokens) is not int or not 1 <= max_tokens <= 256):
            raise ValueError("Chat input exceeds the supported contract")
        if not self.slots.acquire(timeout=self.policy["queue_timeout_seconds"]):
            raise InferenceUnavailable("Chat is busy; retry later")
        try:
            if self._admit_primary():
                try:
                    text = self._generate(self.primary, prompt, system, max_tokens)
                    self._result(True)
                    with self.lock:
                        self.last_provider = self.primary.kind
                    return text
                except (httpx.HTTPError, ValueError, InferenceUnavailable) as exc:
                    log.warning("Chat primary deferred provider=%s category=%s", self.primary.kind, type(exc).__name__)
                    if (isinstance(exc, httpx.HTTPStatusError)
                            and exc.response.status_code < 500
                            and exc.response.status_code not in (408, 429)):
                        self._result(True)
                        with self.lock:
                            self.last_error = "rejected"
                        raise InferenceUnavailable("Chat primary rejected this request") from None
                    self._result(False)
            if self.fallback is None:
                raise InferenceUnavailable("Chat primary is unavailable")
            try:
                text = self._generate(self.fallback, prompt, system, max_tokens)
                with self.lock:
                    self.last_provider = self.fallback.kind
                log.warning("Chat used explicitly configured fallback provider=%s", self.fallback.kind)
                return text
            except (httpx.HTTPError, ValueError, InferenceUnavailable):
                raise InferenceUnavailable("Chat fallback is unavailable") from None
        finally:
            self.slots.release()

    def snapshot(self) -> dict:
        with self.lock:
            return self.snapshot_unlocked()

    def health(self) -> dict:
        with self.lock:
            if self.health_at and time.monotonic() - self.health_at < self.policy["health_cache_seconds"]:
                return {**self.snapshot_unlocked(), **self.health_value}
        try:
            payload = self._request(self.primary, "/health" if self.primary.kind == "aesir" else "/api/tags", None)
            if self.primary.kind == "aesir":
                ready = (payload.get("status") == "ready" and payload.get("capabilities", {}).get("text_generation") is True
                         and payload.get("model") == self.primary.model)
            else:
                models = payload.get("models")
                ready = isinstance(models, list) and any(isinstance(model, dict)
                    and model.get("name", model.get("model")) == self.primary.model for model in models)
            value = {"ready": ready, "embeddings_provider": "ollama"}
        except (httpx.HTTPError, ValueError, TypeError, AttributeError, InferenceUnavailable):
            value = {"ready": False, "embeddings_provider": "ollama"}
        with self.lock:
            self.health_value, self.health_at = value, time.monotonic()
        return {**self.snapshot(), **value}

    def snapshot_unlocked(self) -> dict:
        """Health cache only; called while holding the state lock."""
        return {"configured_provider": self.primary.kind, "fallback_provider": self.fallback.kind if self.fallback else None,
                "last_provider": self.last_provider, "last_error": self.last_error,
                "circuit": "open" if self.open_until > time.monotonic() else "probe" if self.open_until else "closed",
                "retry_after_seconds": max(0, round(self.open_until - time.monotonic(), 1))}


def from_environment(ollama_url: str, model: str) -> ChatRouter:
    policy = load_policy(Path(os.getenv("VIEWER_INFERENCE_POLICY", str(Path(__file__).with_name("inference.json")))))
    kind = os.getenv("VIEWER_CHAT_BACKEND", "ollama")
    url = os.getenv("VIEWER_CHAT_URL", ollama_url if kind == "ollama" else "http://127.0.0.1:18434")
    key = private_key(Path(os.environ["VIEWER_CHAT_API_KEY_FILE"])) if kind == "aesir" else ""
    fallback = os.getenv("VIEWER_CHAT_FALLBACK", "none")
    if fallback not in ("none", "ollama") or kind == "ollama" and fallback != "none":
        raise ValueError("Invalid chat fallback policy")
    return ChatRouter(Provider(kind, url, model, key), policy,
                      Provider("ollama", ollama_url, model) if fallback == "ollama" else None)
