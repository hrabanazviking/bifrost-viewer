"""Last-good retry metadata and process ownership for the private local inbox."""
from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import math
import os
import shutil
import tempfile
import time
from pathlib import Path

log = logging.getLogger("ingest.state")


def atomic_json(path: Path, payload: dict) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            json.dump(payload, stream, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        descriptor = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def valid_record(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    signature = value.get("signature", [])
    if not isinstance(signature, list) or len(signature) not in (2, 4) or any(type(v) is not int or v < 0 for v in signature):
        return False
    attempts, retry = value.get("attempts", 0), value.get("retry_at", 0)
    if type(attempts) is not int or attempts < 0 or not isinstance(retry, (int, float)) or not math.isfinite(retry) or retry < 0:
        return False
    completed = value.get("completed", [])
    return isinstance(completed, list) and all(isinstance(v, str) for v in completed) and type(value.get("permanent", False)) is bool


def load_state(path: Path) -> dict:
    for candidate in (path, path.with_suffix(path.suffix + ".bak")):
        try:
            data = json.loads(candidate.read_text())
            if not isinstance(data, dict):
                raise ValueError("Retry metadata must be an object")
            valid = {key: value for key, value in data.items() if isinstance(key, str) and valid_record(value)}
            if len(valid) != len(data):
                log.warning("Malformed retry records retained in recovery copy; valid records recovered")
                preserve_corrupt(candidate)
            if candidate != path:
                log.warning("Recovered inbox retry metadata from last-good backup")
            if candidate != path or len(valid) != len(data):
                try:
                    atomic_json(path, valid)
                except OSError:
                    log.warning("Recovered metadata in memory; primary state still needs writable storage")
            return valid
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            preserve_corrupt(candidate)
            log.warning("Unreadable inbox metadata; trying last-good copy")
    return {}


def preserve_corrupt(path: Path) -> None:
    if path.exists():
        target = path.with_name(path.name + f".corrupt-{time.time_ns()}")
        try:
            shutil.copy2(path, target)
            target.chmod(0o600)
        except OSError:
            log.warning("Unable to preserve damaged retry metadata")


def save_state(path: Path, state: dict) -> None:
    if path.exists():
        try:
            previous = json.loads(path.read_text())
            if isinstance(previous, dict) and all(valid_record(value) for value in previous.values()):
                atomic_json(path.with_suffix(path.suffix + ".bak"), previous)
        except (OSError, ValueError):
            pass
    atomic_json(path, state)


@contextlib.contextmanager
def exclusive_lock(path: Path):
    with path.open("a") as stream:
        path.chmod(0o600)
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another supervisor owns this inbox; refusing duplicate work") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
