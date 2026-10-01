"""Fetch public web documents using validated, pinned addresses at every hop."""
from __future__ import annotations

import http.client
import ipaddress
import json
import os
import socket
import ssl
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit


def limits() -> dict:
    default = Path(__file__).parents[1] / "security/limits.json"
    values = json.loads(default.read_text()) if default.exists() else {}
    if os.getenv("VIEWER_LIMITS_FILE"):
        values.update(json.loads(Path(os.environ["VIEWER_LIMITS_FILE"]).read_text()))
    if not values:
        raise ValueError("URL fetch limits are missing")
    return values


def destination(url: str) -> tuple[str, str, int, list[str]]:
    if len(url) > 4096 or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("Invalid URL length or control characters")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTP(S) URLs without credentials are supported")
    host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in {80, 443}:
        raise ValueError("Only web ports 80 and 443 are supported")
    addresses = list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("URL resolves to a private, local or reserved address")
    return parsed.scheme, host, port, addresses[:limits()["url_dns_candidates"]]


class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, addresses, port, timeout, tls=False):
        super().__init__(host, port, timeout=timeout)
        self.addresses, self.tls = addresses, tls

    def connect(self):
        error = None
        for address in self.addresses:
            try:
                self.sock = socket.create_connection((address, self.port), self.timeout)
                if self.tls:
                    self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=self.host)
                return
            except OSError as exc:
                error = exc
                if self.sock:
                    self.sock.close()
                    self.sock = None
        raise error or OSError("No validated web addresses")


def fetch_public(url: str) -> str:
    cfg = limits()
    for hop in range(cfg["url_redirects"] + 1):
        scheme, host, port, addresses = destination(url)
        parsed = urlsplit(url)
        target = quote(urlunsplit(("", "", parsed.path or "/", parsed.query, "")), safe="/?&=:%;,+@!$'()*[]~")
        connection = PinnedHTTP(host, addresses, port, cfg["url_timeout_seconds"], scheme == "https")
        try:
            connection.request("GET", target, headers={"Accept-Encoding": "identity", "User-Agent": "Bifrost-Ingest/0.3"})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location or hop == cfg["url_redirects"]:
                    raise ValueError("Invalid or excessive web redirects")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError(f"Web server returned HTTP {response.status}")
            if response.getheader("Content-Encoding", "identity").lower() not in {"", "identity"}:
                raise ValueError("Compressed web responses are not accepted")
            data = response.read(cfg["url_response_bytes"] + 1)
            if len(data) > cfg["url_response_bytes"]:
                raise ValueError("Web document exceeds the response limit")
            return data.decode("utf-8", errors="replace")
        finally:
            connection.close()
    raise ValueError("Excessive redirects")
