"""Bind loopback first so unavailable tailnet interfaces do not prevent use."""
from __future__ import annotations

import logging
import socket
from typing import Any

import uvicorn


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
        server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="info"))
        server.run(sockets=sockets)
    finally:
        for sock in sockets:
            sock.close()
