"""Read only sanitized progress from the existing bounded, private worker log."""
from __future__ import annotations

import json
import math
from pathlib import Path

STAGES = {"parsing", "validating", "embedding", "persisting", "done", "failed"}
CATEGORIES = {20: "dependency", 21: "input", 22: "configuration", 124: "timeout"}


def recent_progress(path: Path, started: float = 0) -> dict:
    try:
        with path.open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 8192))
            lines = stream.read(8192).decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            if "BIFROST_PROGRESS " not in line:
                continue
            result = decoded_progress(line.split("BIFROST_PROGRESS ", 1)[1], started)
            if result:
                return result
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return {}


def decoded_progress(raw: str, started: float) -> dict:
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("stage") not in STAGES:
            return {}
        fraction, updated = float(payload["progress"]), float(payload["updated_at"])
        if not math.isfinite(fraction) or not math.isfinite(updated) or updated < started:
            return {}
        result = {"stage": payload["stage"], "progress": max(0., min(1., fraction))}
        for name in ("doc_id", "chunks", "embedded"):
            if type(payload.get(name)) is int and 0 <= payload[name] <= 2**63 - 1:
                result[name] = payload[name]
        return result
    except (ValueError, TypeError, KeyError):
        return {}


def detail(row: dict, directory: Path) -> dict:
    status = row["status"]
    result = {"stage": status, "progress": 1. if status == "ok" else 0.}
    if status in {"running", "ok"}:
        result.update(recent_progress(directory / (row["id"] + ".log"), row.get("claimed_at") or 0))
    if status == "ok":
        result.update(stage="done", progress=1.)
    result["error_category"] = row.get("error_category")
    result["next_attempt_at"] = row["next_attempt"] if status == "queued" else None
    result["owner_retries"] = row.get("owner_retries", 0)
    return result
