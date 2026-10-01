"""Classified, bounded recovery without altering or discarding source knowledge."""
from __future__ import annotations

import errno
import json
import logging
import os
import random
import tempfile
import time
from pathlib import Path
from typing import Callable, TypeVar

import httpx
import psycopg

log = logging.getLogger("ingest.recovery")
DEFAULTS = json.loads(Path(__file__).with_suffix(".json").read_text())
T = TypeVar("T")


class InputFailure(ValueError):
    """Retain the input; it must be corrected before retrying."""


class ConfigurationFailure(ValueError):
    """Retain work until the owner corrects configuration or dependencies."""


class TemporaryFailure(ValueError):
    """A bounded retry can safely repeat the operation."""


def setting(name: str) -> int:
    raw = os.getenv("INGEST_" + name.upper(), str(DEFAULTS[name]))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ConfigurationFailure(f"INGEST_{name.upper()} must be an integer") from None
    minimum = 0 if name == "chunk_overlap" else 1
    if value < minimum:
        raise ConfigurationFailure(f"INGEST_{name.upper()} is below its supported minimum")
    return value


def required(db: str, url: str, model: str) -> None:
    if not all(isinstance(value, str) and value.strip() for value in (db, url, model)):
        raise ConfigurationFailure("Set INGEST_DB_URL, OLLAMA_URL and INGEST_EMBED_MODEL")
    if not url.startswith(("https://", "http://")):
        raise ConfigurationFailure("OLLAMA_URL must use HTTP or HTTPS")


def failure(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, InputFailure):
        return 21, "input"
    if isinstance(exc, ConfigurationFailure):
        return 22, "configuration"
    if isinstance(exc, (ModuleNotFoundError, PermissionError)):
        return 22, "configuration"
    if isinstance(exc, (TemporaryFailure, httpx.TransportError)):
        return 20, "dependency"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return (20, "dependency") if code in (408, 429) or code >= 500 else (22, "configuration")
    if isinstance(exc, psycopg.Error):
        state = exc.sqlstate or ""
        transient = state.startswith(("08", "40", "53", "57P")) or state == "57014"
        transient |= isinstance(exc, (psycopg.OperationalError, psycopg.InterfaceError)) and not state.startswith("28")
        return (20, "dependency") if transient else (22, "configuration")
    if isinstance(exc, (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError)):
        return 21, "input"
    if isinstance(exc, OSError) and exc.errno in (errno.ENOSPC, errno.EIO, errno.EBUSY):
        return 20, "storage"
    return 1, "unexpected"


def delay(attempt: int) -> None:
    seconds = min(setting("retry_max_seconds"), setting("retry_base_seconds") * 2 ** attempt)
    time.sleep(seconds * random.uniform(.8, 1.2))


def database_retry(operation: Callable[[], T]) -> T:
    attempts = setting("db_attempts")
    for attempt in range(attempts):
        try:
            return operation()
        except psycopg.Error as exc:
            if failure(exc)[0] != 20 or attempt + 1 == attempts:
                raise
            log.warning("Database operation deferred kind=%s attempt=%s", type(exc).__name__, attempt + 1)
            delay(attempt)
    raise TemporaryFailure("Database retry budget exhausted")


def source_signature(source: str) -> tuple | None:
    if source.startswith(("https://", "http://")):
        return None
    path = Path(source).expanduser().resolve()
    stat = path.stat()
    if not path.is_file():
        raise InputFailure("Source must be a regular file")
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def check_source(source: str, expected: tuple | None) -> None:
    if expected is not None and source_signature(source) != expected:
        raise TemporaryFailure("Source changed during ingestion; retain it and retry when stable")


def progress(stage: str, fraction: float, **details: int | str) -> None:
    if stage not in DEFAULTS["progress_stages"]:
        raise ValueError("Unknown ingestion stage")
    payload = {"stage": stage, "progress": max(0., min(1., fraction)), "updated_at": time.time(), **details}
    log.info("BIFROST_PROGRESS %s", json.dumps(payload))
    destination = os.getenv("INGEST_PROGRESS_FILE")
    if not destination:
        return
    path, temporary = Path(destination), None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except OSError as exc:
        log.warning("Progress persistence unavailable kind=%s", type(exc).__name__)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
