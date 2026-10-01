"""HTTP admission before body parsing; bearer scopes, quotas, origins and transport."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import socket
import time
from urllib.parse import parse_qs, urlsplit

from security.store import AccessError, digest

PUBLIC = {"/api/auth/recovery/request", "/api/auth/recovery/confirm"}


def supplied_token(scope):
    headers = {k.lower(): v for k, v in scope["headers"]}
    auth = headers.get(b"authorization", b"").decode("latin1")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return parse_qs(scope.get("query_string", b"").decode("latin1")).get("token", [""])[0]


def scope_needed(method, path):
    if path.startswith("/api/admin/") or path == "/api/cluster-names":
        return "admin"
    if method == "POST":
        return "ingest" if path in {"/api/ingest/url", "/api/ingest/text"} else "admin"
    return "read"


def authorize(store, scope):
    principal = store.authenticate(supplied_token(scope))
    if scope_needed(scope["method"], scope["path"]) not in principal.scopes:
        raise AccessError("This key does not grant the required permission")
    return principal


class SecurityGateway:
    def __init__(self, app, get_store, host):
        self.app, self.get_store = app, get_store
        try:
            self.tailnet_listener = ipaddress.ip_address(host) in ipaddress.ip_network("100.64.0.0/10") or ipaddress.ip_address(host) in ipaddress.ip_network("fd7a:115c:a1e0::/48")
        except ValueError:
            self.tailnet_listener = False
        self.hosts = {"localhost", "127.0.0.1", "::1", socket.gethostname().lower(), host.lower()}
        self.hosts.update(value.strip().lower() for value in os.getenv("VIEWER_ALLOWED_HOSTS", "").split(",") if value.strip())
        self.origins = {value.strip() for value in os.getenv("VIEWER_ALLOWED_ORIGINS", "").split(",") if value.strip()}
        self.expensive = 0  # accessed only on the ASGI event loop

    def _boundary(self, scope, headers):
        host = headers.get(b"host", b"").decode("latin1")
        hostname = urlsplit("//" + host).hostname
        if not hostname or hostname.lower() not in self.hosts:
            raise AccessError("Unrecognized Host", 400)
        peer = scope.get("client", ("", 0))[0]
        if peer != "testclient":
            try:
                ip = ipaddress.ip_address(peer)
            except ValueError:
                raise AccessError("Unrecognized network peer", 403) from None
            tailnet = ip in ipaddress.ip_network("100.64.0.0/10") or ip in ipaddress.ip_network("fd7a:115c:a1e0::/48")
            encrypted_tailnet = tailnet and self.tailnet_listener and scope.get("server", ("", 0))[0] not in {"0.0.0.0", "::"}
            if scope["scheme"] != "https" and not ip.is_loopback and not encrypted_tailnet:
                raise AccessError("HTTPS is required outside loopback or the encrypted tailnet", 403)
        origin = headers.get(b"origin", b"").decode("latin1")
        if origin and origin != scope["scheme"] + "://" + host and origin not in self.origins:
            raise AccessError("Origin is not allowed", 403)
        return origin

    async def _reply(self, send, status, message, retry=0):
        headers = [(b"content-type", b"application/json"), (b"cache-control", b"no-store")]
        if retry:
            headers.append((b"retry-after", str(retry).encode()))
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": json.dumps({"error": message}).encode()})

    async def _preflight(self, send):
        await send({"type": "http.response.start", "status": 204, "headers": [
            (b"access-control-allow-methods", b"GET, POST, OPTIONS"),
            (b"access-control-allow-headers", b"Authorization, Content-Type, Idempotency-Key")]})
        await send({"type": "http.response.body", "body": b""})

    def _admit(self, store, scope):
        if scope["path"] == "/.well-known/bifrost.json":
            if scope["method"] != "GET":
                raise AccessError("Discovery supports GET only", 405)
            window = str(int(time.time() // 3600))
            self._global_budget(store, window)
            peer = scope.get("client", ("", 0))[0]
            store.spend("discovery:" + digest(peer), window + ":discovery", store.limits["discovery_requests_per_hour"])
            return False
        if not scope["path"].startswith("/api/"):
            return False
        peer, window = scope.get("client", ("", 0))[0], str(int(time.time() // 3600))
        if scope["path"] in PUBLIC:
            self._global_budget(store, window)
            store.spend("public:" + digest(peer), window + ":public", store.limits["public_requests_per_hour"])
            return False
        try:
            principal = authorize(store, scope)
        except AccessError:
            self._global_budget(store, window)
            store.spend("invalid:" + digest(peer), window + ":invalid", store.limits["invalid_auth_per_hour"])
            raise
        if "admin" not in principal.scopes:
            self._global_budget(store, window)
        scope.setdefault("state", {})["principal"] = principal
        costs = {"/api/search": "query_request_cost", "/api/skry": "query_request_cost",
                 "/api/path": "query_request_cost", "/api/ingest/url": "query_request_cost",
                 "/api/graph": "graph_request_cost", "/api/skein/graph": "graph_request_cost"}
        cost = store.limits[costs[scope["path"]]] if scope["path"] in costs else 1
        store.rate(principal, cost)
        expensive = cost > 1 or scope["path"] == "/api/cluster-names"
        if expensive and self.expensive >= store.limits["expensive_concurrency"]:
            raise AccessError("Busy; retry this query later", 429, 5)
        return expensive

    def _global_budget(self, store, window):
        store.spend("global-untrusted", window + ":minute:" + str(int(time.time() // 60)),
                    store.limits["global_untrusted_requests_per_minute"])

    async def _body(self, receive, cfg):
        body = bytearray()
        async with asyncio.timeout(cfg["body_timeout_seconds"]):
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return None
                body.extend(message.get("body", b""))
                if len(body) > cfg["body_bytes"]:
                    raise AccessError("Request body too large", 413)
                if not message.get("more_body"):
                    return bytes(body)

    def _receive(self, body, receive):
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        return bounded_receive

    def _sender(self, origin, scope, send):
        async def secure_send(message):
            if message["type"] == "http.response.start":
                extra = [(b"referrer-policy", b"no-referrer"), (b"x-content-type-options", b"nosniff"),
                         (b"x-frame-options", b"DENY"), (b"cache-control", b"no-store")]
                if scope["scheme"] == "https":
                    extra.append((b"strict-transport-security", b"max-age=31536000"))
                policy = "default-src 'self'; script-src 'self' https://unpkg.com 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
                extra.append((b"content-security-policy", policy.encode()))
                if origin:
                    extra.extend([(b"access-control-allow-origin", origin.encode()), (b"vary", b"Origin"), (b"access-control-expose-headers", b"Retry-After")])
                message["headers"] = message.get("headers", []) + extra
            await send(message)
        return secure_send

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        store, acquired = self.get_store(), False
        cfg = store.limits
        response_send = self._sender("", scope, send)
        try:
            if sum(len(k) + len(v) for k, v in scope["headers"]) > cfg["header_bytes"]:
                raise AccessError("Request headers too large", 431)
            headers = {k.lower(): v for k, v in scope["headers"]}
            origin = self._boundary(scope, headers)
            response_send = self._sender(origin, scope, send)
            if scope["method"] == "OPTIONS" and origin:
                return await self._preflight(response_send)
            expensive = self._admit(store, scope)
            if int(headers.get(b"content-length", b"0")) > cfg["body_bytes"]:
                raise AccessError("Request body too large", 413)
            if expensive:
                self.expensive += 1
                acquired = True
            body = await self._body(receive, cfg)
            if body is not None:
                await self.app(scope, self._receive(body, receive), self._sender(origin, scope, send))
        except AccessError as exc:
            await self._reply(response_send, exc.status, str(exc), exc.retry)
        except (ValueError, UnicodeError):
            await self._reply(response_send, 400, "Malformed request")
        except TimeoutError:
            await self._reply(response_send, 408, "Request body timeout")
        finally:
            if acquired:
                self.expensive = max(0, self.expensive - 1)
