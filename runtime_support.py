"""Atomic derived-state publication; existing files survive failed writes."""
from __future__ import annotations

import os
import logging
import tempfile
from pathlib import Path
from typing import Any

import orjson

log = logging.getLogger("bifrost.cache")


def atomic_json(path: Path, payload: Any) -> None:
    data = orjson.dumps(payload, option=orjson.OPT_SERIALIZE_NUMPY)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        if hasattr(os, "O_DIRECTORY"):
            descriptor = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def valid_graph(payload: Any, fingerprint: str) -> bool:
    if not isinstance(payload, dict):
        return False
    for level in ("chunk", "document"):
        graph = payload.get(level)
        if not isinstance(graph, dict) or graph.get("fingerprint") != fingerprint:
            return False
        if not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("links"), list):
            return False
    return True


def publish_graph(path: Path, payload: Any, prefix: str) -> None:
    """Reclaim obsolete generated layouts only after a replacement is durable."""
    atomic_json(path, payload)
    published = path.stat().st_mtime_ns
    for old in path.parent.glob(prefix + "*.json"):
        if old == path:
            continue
        try:
            if old.stat().st_mtime_ns <= published:
                old.unlink()
        except OSError:
            log.warning("Obsolete generated cache retained: %s", old.name)
