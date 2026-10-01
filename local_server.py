"""Bind loopback first so unavailable tailnet interfaces do not prevent use."""
from __future__ import annotations

import logging
import os
import socket
from typing import Any

import uvicorn
from security.store import load_limits


def serve(app: Any, *, host: str, loopback: str, port: int) -> None:
    hosts = list(dict.fromkeys([loopback, host])) if loopback else [host]
    if host in ("0.0.0.0", "::"):
        hosts = [host]
    sockets = []
    try:
        for address in hosts:
            sock = socket.socket(socket.AF_INET6 if ":" in address else socket.AF_INET)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((address, port))
                sock.listen(128)
                sockets.append(sock)
            except OSError:
                sock.close()
                if address == loopback or not sockets:
                    raise
                logging.getLogger("bifrost").warning("listener unavailable: %s; loopback remains usable", address)
        cert, key = os.getenv("VIEWER_TLS_CERT"), os.getenv("VIEWER_TLS_KEY")
        if bool(cert) != bool(key):
            raise ValueError("Configure both VIEWER_TLS_CERT and VIEWER_TLS_KEY")
        server = uvicorn.Server(uvicorn.Config(
            app, port=port, log_level="info", proxy_headers=False, access_log=False,
            limit_concurrency=load_limits()["server_concurrency"], timeout_keep_alive=5,
            h11_max_incomplete_event_size=load_limits()["header_bytes"],
            ssl_certfile=cert, ssl_keyfile=key))
        server.run(sockets=sockets)
    finally:
        for sock in sockets:
            sock.close()
