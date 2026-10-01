"""Dependency-free, bounded REST client for individually authorized Bifröst AIs."""
from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import logging
import os
import random
import re
import ssl
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

log = logging.getLogger("bifrost.client")
POLICY = json.loads(Path(__file__).with_name("policy.json").read_text())


class ClientError(Exception):
    """Safe failure information without a token, URL query, payload or traceback."""
    def __init__(self, message: str, status: int = 0, retry_after: float = 0):
        super().__init__(message)
        self.status, self.retry_after = status, retry_after


def validated_base(value: str) -> str:
    try:
        url = urlsplit(value.strip().rstrip("/"))
        port, host = url.port, url.hostname or ""
    except ValueError:
        raise ClientError("Invalid server address") from None
    if (url.scheme not in {"http", "https"} or not host or url.username or url.password
        or url.path or url.query or url.fragment or "\\" in value or "'" in value
        or any(c.isspace() for c in value) or not re.fullmatch(r"[A-Za-z0-9.:-]+", host) or (port is not None and not 1 <= port <= 65535)):
        raise ClientError("Use an HTTP(S) origin without credentials, path, query or fragment")
    try:
        ip = ipaddress.ip_address(host)
        local = ip.is_loopback or ip in ipaddress.ip_network("100.64.0.0/10") or ip in ipaddress.ip_network("fd7a:115c:a1e0::/48")
    except ValueError:
        local = host == "localhost" or host.endswith(".ts.net")
    if url.scheme == "http" and not local:
        raise ClientError("Remote access requires HTTPS or an encrypted tailnet address")
    return url.geturl()


def retry_delay(value: str | None, now: float) -> float:
    try:
        return max(0, float(value or ""))
    except ValueError:
        try:
            return max(0, parsedate_to_datetime(value or "").timestamp() - now)
        except (ValueError, TypeError, OverflowError):
            return 0


class BifrostClient:
    def __init__(self, base_url: str, token: str, *, exchange=None, sleep=time.sleep,
                 clock=time.monotonic, wall_clock=time.time):
        self.base = validated_base(base_url)
        if not token or len(token) > 256 or any(c.isspace() for c in token):
            raise ClientError("Set an individual AI key in BIFROST_TOKEN")
        if token.startswith("bfo_"):
            raise ClientError("Owner credentials cannot be used by the agent client; issue an AI key")
        self._token = token
        self.exchange = exchange or self._exchange
        self.sleep, self.clock, self.wall_clock = sleep, clock, wall_clock

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("BIFROST_BASE_URL", ""), os.environ.get("BIFROST_TOKEN", ""))

    def _exchange(self, method, path, headers, body, timeout):
        url = urlsplit(self.base)
        connection = (http.client.HTTPSConnection(url.hostname, url.port, timeout=timeout, context=ssl.create_default_context())
                      if url.scheme == "https" else http.client.HTTPConnection(url.hostname, url.port, timeout=timeout))
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = self._read_response(response, connection, timeout)
            return response.status, {k.lower(): v for k, v in response.getheaders()}, raw
        finally:
            connection.close()


    def _read_response(self, response, connection, timeout):
        deadline, raw = self.clock() + timeout, bytearray()
        while True:
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise TimeoutError("Response deadline reached")
            if connection.sock:
                connection.sock.settimeout(remaining)
            part = response.read1(min(65536, POLICY["max_response_bytes"] + 1 - len(raw)))
            raw.extend(part)
            if len(raw) > POLICY["max_response_bytes"]:
                raise ClientError("Response exceeds the client safety limit")
            if not part:
                return bytes(raw)

    def request(self, path: str, body: dict | None = None, *, key: str | None = None) -> dict | list:
        if not path.startswith("/api/") or path.startswith("/api/admin/") or any(c in path for c in "\r\n"):
            raise ClientError("Agent requests must use a non-administration API path")
        if body is not None and (path not in {"/api/ingest/text", "/api/ingest/url"} or not key or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}", key)):
            raise ClientError("Append requests require a stable 8–128 character Idempotency-Key")
        headers = {"Authorization": "Bearer " + self._token, "Accept": "application/json"}
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        if payload is not None:
            headers.update({"Content-Type": "application/json", "Idempotency-Key": key})
        deadline, error = self.clock() + POLICY["retry_deadline_seconds"], None
        for attempt in range(POLICY["max_attempts"]):
            remaining = deadline - self.clock()
            if remaining <= 0:
                break
            try:
                status, response_headers, raw = self.exchange("GET" if body is None else "POST", path, headers, payload,
                    min(POLICY["request_timeout_seconds"], remaining))
                if 200 <= status < 300:
                    return self._decode(raw)
                error = self._failure(status, response_headers, raw)
            except (OSError, http.client.HTTPException, TimeoutError):
                error = ClientError("Connection interrupted; retain the original append ID and payload")
            if error.status not in {0, 429, 502, 503, 504}:
                raise error
            delay = max(error.retry_after, 2 ** attempt + random.uniform(0, .5))
            if attempt + 1 == POLICY["max_attempts"] or delay >= deadline - self.clock():
                break
            self.sleep(delay)
        raise error or ClientError("Request deadline reached")

    def _decode(self, raw):
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError):
            raise ClientError("Server returned invalid JSON; no automatic replay") from None

    def _failure(self, status, headers, raw):
        message = {401: "Access expired or invalid; ask the owner for an AI key",
                   403: "Permission denied; ask the owner to check scopes",
                   409: "Operation ID conflicts with another payload; investigate before resubmitting",
                   413: "Request too large; reduce the submission", 422: "Invalid request fields"}.get(status)
        if 300 <= status < 400:
            message = "Redirect refused; verify the configured server address with the owner"
        return ClientError(message or f"Server returned HTTP {status}", status,
                           retry_delay(headers.get("retry-after"), self.wall_clock()))

    def identity(self):
        return self.request("/api/auth/me")

    def capabilities(self):
        return self.request("/api/capabilities")

    def health(self):
        return self.request("/api/health")

    def search(self, query: str, k: int = 6):
        if not query.strip() or len(query) > 10000 or not 1 <= k <= 100:
            raise ClientError("Provide a nonempty query up to 10000 characters and k from 1 to 100")
        return self.request("/api/search?" + urlencode({"q": query, "k": k, "hyde": 0}))

    def chunk(self, chunk_id: int):
        if chunk_id < 1:
            raise ClientError("Passage ID must be positive")
        return self.request("/api/chunk/" + str(chunk_id))

    def add_text(self, title: str, text: str, operation_id: str):
        return self.request("/api/ingest/text", {"title": title, "text": text}, key=operation_id)

    def add_url(self, url: str, operation_id: str):
        return self.request("/api/ingest/url", {"url": url}, key=operation_id)

    def jobs(self):
        return self.request("/api/ingest/jobs")

    def job(self, job_id: str):
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise ClientError("Invalid job ID")
        return self.request("/api/ingest/jobs/" + quote(job_id, safe=""))

    def wait(self, job_id: str, seconds: int = POLICY["poll_deadline_seconds"]):
        if not 1 <= seconds <= POLICY["poll_deadline_seconds"]:
            raise ClientError("Polling deadline must be within the configured client limit")
        deadline = self.clock() + seconds
        while self.clock() < deadline:
            result = self.job(job_id)
            if result["status"] in {"ok", "failed"}:
                return result
            remaining = deadline - self.clock()
            if remaining <= 0:
                break
            self.sleep(min(POLICY["poll_seconds"], remaining))
        raise ClientError("Polling deadline reached; the server job may still be running. Check the same job later")


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    for name in ("health", "identity", "capabilities", "jobs"):
        sub.add_parser(name)
    search = sub.add_parser("search"); search.add_argument("query"); search.add_argument("--k", type=int, default=6)
    chunk = sub.add_parser("chunk"); chunk.add_argument("id", type=int)
    for name in ("job", "wait"):
        sub.add_parser(name).add_argument("id")
    note = sub.add_parser("add-text"); note.add_argument("--title", required=True); note.add_argument("--file", type=Path, required=True); note.add_argument("--id", required=True)
    url = sub.add_parser("add-url"); url.add_argument("url"); url.add_argument("--id", required=True)
    return cli


def run(cli, client):
    if cli.command == "search":
        return client.search(cli.query, cli.k)
    if cli.command == "chunk":
        return client.chunk(cli.id)
    if cli.command in {"job", "wait"}:
        return getattr(client, cli.command)(cli.id)
    if cli.command == "add-text":
        if cli.file.stat().st_size > 200000:
            raise ClientError("Note file must fit within 200000 UTF-8 bytes")
        return client.add_text(cli.title, cli.file.read_text(encoding="utf-8"), cli.id)
    if cli.command == "add-url":
        return client.add_url(cli.url, cli.id)
    return getattr(client, cli.command)()


def main():
    logging.basicConfig(level=logging.WARNING)
    try:
        result = run(parser().parse_args(), BifrostClient.from_env())
        # Machine-readable stdout is the CLI's public interface, not logging.
        import sys
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except (ClientError, OSError, UnicodeError) as exc:
        log.error("%s", str(exc) if isinstance(exc, ClientError) else "Could not read the local UTF-8 note file")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
